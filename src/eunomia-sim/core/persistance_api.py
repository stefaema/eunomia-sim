from peewee import *
import json
from collections import deque

INPUT_DENOM = ("input")
OUTPUT_DENOM = ("output")

db = SqliteDatabase('system.db')


class BaseModel(Model):
    """Modelo base para no repetir la conexión a la DB."""
    class Meta:
        database = db

class Commit(BaseModel):
    """Commits para versionar el estado del sistema."""
    id = AutoField()
    message = CharField()
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

class Change(BaseModel):
    """Cambios individuales dentro de un commit."""
    id = AutoField()
    commit = ForeignKeyField(Commit, backref='changes')
    change_type = CharField()  # e.g., 'add_node', 'remove_node', 'update_port'
    details = TextField()  # JSON string with details of the change

class NodeType(BaseModel):
    """Tipos de nodos: fisico, simulado o virtual."""
    name = CharField(unique=True)


class Node(BaseModel):
    """Nodos en el sistema."""
    id = AutoField()
    name = CharField()
    node_type = ForeignKeyField(NodeType, backref='nodes')
    pos_x = IntegerField(default=50)
    pos_y = IntegerField(default=50)


class Port(BaseModel):
    """Puertos de comunicación los nodos."""
    id = AutoField()
    node = ForeignKeyField(Node, backref='ports')
    port_name = CharField()
    port_type = CharField(choices=[INPUT_DENOM, OUTPUT_DENOM])


class PortParameter(BaseModel):
    """Parámetros de los puertos."""
    id = AutoField()
    port = ForeignKeyField(Port, backref='parameters')
    key = CharField()
    value = CharField()


class Connection(BaseModel):
    """Conexiones entre puertos de nodos."""
    id = AutoField()
    from_port = ForeignKeyField(Port, backref='outgoing_connections')
    to_port = ForeignKeyField(Port, backref='incoming_connections')
    protocol = CharField(default="MQTT")  # Opcional: protocolo de comunicación, default is JSON over MQTT


class NodeCallback(BaseModel):
    """Callbacks asociados a nodos: Qué hace un nodo virtual o simulado."""
    id = AutoField()
    node = ForeignKeyField(Node, backref='callback')
    callback_name = CharField()



CALLBACKS = {}


def callback(name):
    """Decorador para registrar callbacks de nodos."""
    def decorator(func):
        CALLBACKS[name] = func
        return func
    return decorator


def run_node(node: Node):
    """Ejecuta el callback de un nodo y propaga sus salidas."""
    cb = NodeCallback.get_or_none(node=node)
    if not cb:
        return {}

    func = CALLBACKS.get(cb.callback_name)
    if not func:
        raise ValueError(f"Callback {cb.callback_name} no registrado")

    # Cargar entradas como dict
    inputs = {}
    for port in node.ports.where(Port.port_type == "input"):
        params = {p.key: _auto_cast(p.value) for p in port.parameters}
        inputs[port.port_name] = params

    outputs = func(inputs)  # Ejecuta la lógica del nodo
    if not outputs:
        return {}

    # Actualizar parámetros de puertos de salida
    for port_name, param_dict in outputs.items():
        port = Port.get_or_none(node=node, port_name=port_name, port_type="output")
        if port:
            for key, value in param_dict.items():
                pp, created = PortParameter.get_or_create(port=port, key=key)
                pp.value = str(value)
                pp.save()

    # Propagar valores a nodos conectados
    connected_nodes = set()
    for port_name, param_dict in outputs.items():
        port = Port.get_or_none(node=node, port_name=port_name, port_type="output")
        if not port:
            continue
        for conn in port.outgoing_connections:
            to_port = conn.to_port
            # copiar parámetros al puerto de entrada conectado
            for key, value in param_dict.items():
                pp, _ = PortParameter.get_or_create(port=to_port, key=key)
                pp.value = str(value)
                pp.save()
            connected_nodes.add(to_port.node)

    return connected_nodes


def run_cascade(start_node: Node):
    """Ejecuta un nodo y todos los que se vean afectados por su salida."""
    with db.atomic():
        queue = deque([start_node])
        visited = set()
        while queue:
            node = queue.popleft()
            if node.id in visited:
                continue
            visited.add(node.id)
            next_nodes = run_node(node)
            for n in next_nodes:
                if n.id not in visited:
                    queue.append(n)


def _auto_cast(value: str):
    """Convierte strings simples a tipos nativos si es posible."""
    if value.isdigit():
        return int(value)
    try:
        return float(value)
    except ValueError:
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        return value


# === INIT DB ===
def init_db():
    db.connect()
    db.create_tables([NodeType, Node, Port, PortParameter, Connection, NodeCallback])

    # Tipos
    physical, _ = NodeType.get_or_create(name="FISICA")
    simulated, _ = NodeType.get_or_create(name="SIM")
    virtual, _ = NodeType.get_or_create(name="VIRTUAL")

    # Nodos físicos iniciales
    accs, _ = Node.get_or_create(name="Sistema Autonomo de Control Central", node_type=physical)
    solar_plant, _ = Node.get_or_create(name="Planta de Generacion Solar Principal", node_type=physical)
    thermal_plant, _ = Node.get_or_create(name="Planta de Energia Termica de Respaldo", node_type=physical)

    # Crear puertos para solar y accs
    solar_out, _ = Port.get_or_create(node=solar_plant, port_name="CTRL #1", port_type="output")

    for i in range(1, 4):
        Port.get_or_create(node=accs, port_name=f"CTRL #{i}", port_type="input")


    thermal_out, _ = Port.get_or_create(node=thermal_plant, port_name="CTRL #1", port_type="output")


    # Conectar solar → accs
    Connection.get_or_create(from_port=solar_out, to_port=Port.get_or_none(node=accs, port_name="CTRL #1"))
    print("Database initialized with default nodes and connections.")
    db.close()

if __name__ == "__main__":
    init_db()
