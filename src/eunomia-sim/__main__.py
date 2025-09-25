import dearpygui.dearpygui as dpg
from .core.persistance_api import *

def key_press_handler(sender, key_code):
    """Maneja teclas presionadas para mejorar la UX."""
    if key_code == dpg.mvKey_Delete or key_code == dpg.mvKey_Back:
        selected_links = dpg.get_selected_links(node_editor="node_editor")
        for link in selected_links:
            delink_callback(sender="node_editor", app_data=link)

# LÓGICA DE LA INTERFAZ (DearPyGUI)

def build_gui_from_db(editor_tag):
    """
    Construye nodos, puertos y conexiones en la GUI.
    """
    db.connect(reuse_if_open=True)
    
    for node in Node.select(): # Para todos los nodos en la DB
        node_label = f"[{NodeType.get_by_id(node.node_type).name}] {node.name} - #{node.id}"

        with dpg.node(label=node_label, parent=editor_tag, pos=[node.pos_x, node.pos_y], tag=f"node_{node.id}"):  # Creamos un nodo GUI para cada nodo DB

            for port in node.ports.order_by(Port.port_type.desc()): 
                attr_type = dpg.mvNode_Attr_Output if port.port_type == OUTPUT_DENOM else dpg.mvNode_Attr_Input
                
                with dpg.node_attribute(label=port.port_name, attribute_type=attr_type, tag=f"port_{port.id}"): #Creamos los puertos como atributos de nodos
                    dpg.add_text(f"Port: {port.port_name}")

    #Conectamos nodos según las conexiones en la DB
    for conn in Connection.select():
        from_port_tag = f"port_{conn.from_port.id}"
        to_port_tag = f"port_{conn.to_port.id}"
        
        # Verificacion de existencia en GUI
        if dpg.does_item_exist(from_port_tag) and dpg.does_item_exist(to_port_tag):
            dpg.add_node_link(from_port_tag, to_port_tag, parent=editor_tag)

    db.close()


def link_callback(sender, app_data):
    """Se ejecuta cuando el usuario CREA un enlace en la GUI."""
    print(app_data)
    from_port_tag = dpg.get_item_alias(app_data[0])
    to_port_tag = dpg.get_item_alias(app_data[1])

    print(f"Intentando crear conexión en DB: {from_port_tag} -> {to_port_tag}")
    
    
    # Extraer IDs de la DB desde los tags de DPG (ej. "port_1" -> 1)
    from_port_id = int(from_port_tag.split('_')[1])
    to_port_id = int(to_port_tag.split('_')[1])

    try:
        db.connect(reuse_if_open=True)
        with db.atomic(): # Transacción para seguridad
            # Obtener los objetos Port desde la DB
            from_port = Port.get_by_id(from_port_id)
            to_port = Port.get_by_id(to_port_id)

            # Validar que la conexión sea válida (Output -> Input)
            if from_port.port_type == OUTPUT_DENOM and to_port.port_type == INPUT_DENOM:
                # Crear la conexión en la base de datos
                Connection.create(from_port=from_port, to_port=to_port)
                # Si la creación en DB es exitosa, añadir el enlace a la GUI
                dpg.add_node_link(from_port_tag, to_port_tag, parent=sender)
                print(f"Conexión creada en DB: Puerto {from_port_id} -> Puerto {to_port_id}")
            else:
                print("Error: Conexión inválida (debe ser de un puerto Output a uno Input).")

    except DoesNotExist:
        print(f"Error: No se encontró el puerto con ID {from_port_id} o {to_port_id} en la DB.")
    except Exception as e:
        print(f"Error al crear la conexión en la DB: {e}")
    finally:
        if not db.is_closed():
            db.close()


def delink_callback(sender, app_data):
    """Se ejecuta cuando el usuario ELIMINA un enlace en la GUI."""
    print(f"Intentando eliminar conexión en DB: {app_data}")
    print(app_data)
    
    # Obtener los puertos que este enlace conecta
    config = dpg.get_item_configuration(app_data)
    print(f"Link config: {config}")
    from_port_tag, to_port_tag = dpg.get_item_alias(config["attr_1"]), dpg.get_item_alias(config["attr_2"])

    # Extraer IDs de la DB
    from_port_id = int(from_port_tag.split('_')[1])
    to_port_id = int(to_port_tag.split('_')[1])

    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            # Buscar y eliminar la conexión en la base de datos
            query = Connection.delete().where(
                (Connection.from_port == from_port_id) & 
                (Connection.to_port == to_port_id)
            )
            deleted_rows = query.execute()

            if deleted_rows > 0:
                # Si se borró de la DB, borrar el item de la GUI
                dpg.delete_item(app_data)
                print(f"Conexión eliminada de la DB: Puerto {from_port_id} -> Puerto {to_port_id}")
            else:
                print("Error: La conexión a eliminar no se encontró en la DB.")
    
    except Exception as e:
        print(f"Error al eliminar la conexión de la DB: {e}")
    finally:
        if not db.is_closed():
            db.close()


def save_node_positions():
    """Guarda la posición actual de todos los nodos en la DB."""
    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            for node_db in Node.select():
                node_tag = f"node_{node_db.id}"
                if dpg.does_item_exist(node_tag):
                    pos = dpg.get_item_pos(node_tag)
                    # Solo guardar si la posición cambió
                    if node_db.pos_x != int(pos[0]) or node_db.pos_y != int(pos[1]):
                        node_db.pos_x = int(pos[0])
                        node_db.pos_y = int(pos[1])
                        node_db.save()
        print("Posiciones de nodos guardadas.")
    except Exception as e:
        print(f"Error al guardar posiciones: {e}")
    finally:
        if not db.is_closed():
            db.close()


# ==============================================================================
# CONFIGURACIÓN Y EJECUCIÓN DE LA APLICACIÓN
# ==============================================================================

def main():
    """Punto de entrada principal de la aplicación."""
    # Inicializar DB si no existe
    try:
        db.connect()
        # Comprobar si las tablas existen
        if not db.table_exists('node'):
             print("Base de datos no encontrada o vacía. Inicializando...")
             db.close() # Cerrar, ya que init_db() la volverá a abrir
             init_db()
    finally:
        if not db.is_closed():
            db.close()


    dpg.create_context()

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=key_press_handler)

    with dpg.window(label="Eunomia - Dossier de Accion", tag="Primary Window"):

        with dpg.window(label="Controles", width=1200, height=50, pos=[0, 0]):
            dpg.add_button(label="Guardar Posiciones", callback=save_node_positions)

        with dpg.group(horizontal=True):
            with dpg.window(label="Nodos", width=1000, height=600, pos=[0, 50]):
                with dpg.node_editor(callback=link_callback, delink_callback=delink_callback, tag="node_editor"):
                    # Esta función llenará el editor con los datos de la DB
                    build_gui_from_db("node_editor")

            with dpg.window(label="Panel de Nodos", width=200, height=600, pos=[1010, 50]):
                dpg.add_button(label="Añadir Nodo")
                dpg.add_button(label="Eliminar Nodo")
                dpg.add_button(label="Configurar Nodo")

    dpg.create_viewport(title='Eunomia - Dossier de Acción', width=1200, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    
    # Bucle principal de la aplicación
    while dpg.is_dearpygui_running():
        # Aquí podrías añadir lógica que se ejecute en cada frame si es necesario
        dpg.render_dearpygui_frame()

    # --- Limpieza al cerrar la aplicación ---
    print("Cerrando aplicación y guardando estado final...")
    save_node_positions()
    dpg.destroy_context()

if __name__ == '__main__':
    main()
