import dearpygui.dearpygui as dpg
from .core.persistance_api import *


def add_port_to_node():
    """Añade un puerto a un nodo seleccionado en la DB y la GUI."""
    node_selection = str(dpg.get_value("node_select")).split(": ")[-1].strip()
    print(node_selection)
    port_name = dpg.get_value("port_name")
    port_type = dpg.get_value("port_type")

    print(f"Adding port '{port_name}' of type '{port_type}' to node '{node_selection}'")
    if not node_selection or not port_name or not port_type:
        print("Error: Nodo, nombre del puerto o tipo de puerto no especificado.")
        return

    node_id = int(node_selection.split('_')[-1])
    
    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            node = Node.get_by_id(node_id)
            new_port = Port.create(node=node, port_name=port_name, port_type=port_type)

        print(f"Puerto '{port_name}' de tipo '{port_type}' añadido al nodo ID {node_id}.")

        # Añadir el nuevo puerto a la GUI
        node_tag = f"node_{node.id}"
        if dpg.does_item_exist(node_tag):
            attr_type = dpg.mvNode_Attr_Output if port_type == OUTPUT_DENOM else dpg.mvNode_Attr_Input
            with dpg.node_attribute(label=new_port.port_name, attribute_type=attr_type, parent=node_tag, tag=f"port_{new_port.id}"):
                dpg.add_text(f"Port: {new_port.port_name}")

    except Exception as e:
        print(f"Error al añadir el puerto: {e}")
    finally:
        if not db.is_closed():
            db.close()
    
    dpg.delete_item("add_ports_modal")


def confirm_remove_nodes(selected_nodes):
    """Elimina nodos seleccionados de la DB y la GUI."""
    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            for node_tag in selected_nodes:
                node_id = int(dpg.get_item_alias(node_tag).split('_')[1])
                node = Node.get_by_id(node_id)
                
                # Eliminar conexiones asociadas
                Connection.delete().where(
                    (Connection.from_port.in_(Port.select().where(Port.node == node))) |
                    (Connection.to_port.in_(Port.select().where(Port.node == node)))
                ).execute()
                
                # Eliminar puertos asociados
                Port.delete().where(Port.node == node).execute()
                
                # Finalmente, eliminar el nodo
                node.delete_instance(recursive=True)
                
                # Eliminar el nodo de la GUI
                if dpg.does_item_exist(node_tag):
                    dpg.delete_item(node_tag)

        print(f"Nodos eliminados: {selected_nodes}")
    except Exception as e:
        print(f"Error al eliminar nodos: {e}")
    finally:
        if not db.is_closed():
            db.close()
    
    dpg.delete_item("remove_node_modal")

def confirm_remove_port():
    """Elimina un puerto seleccionado de la DB y la GUI."""
    port_selection = dpg.get_value("port_to_remove")
    node_selection = str(dpg.get_value("port_rm_node_select")).split(": ")[-1].strip()
    
    if not port_selection or not node_selection:
        print("Error: Puerto o nodo no especificado.")
        return

    port_id = int(port_selection.split("ID: ")[-1].strip(")"))
    node_id = int(node_selection.split('_')[-1])
    
    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            port = Port.get_by_id(port_id)
            
            # Eliminar conexiones asociadas
            Connection.delete().where(
                (Connection.from_port == port) | 
                (Connection.to_port == port)
            ).execute()
            
            # Eliminar el puerto
            port.delete_instance(recursive=True)
            
            # Eliminar el puerto de la GUI
            port_tag = f"port_{port_id}"
            if dpg.does_item_exist(port_tag):
                dpg.delete_item(port_tag)

        print(f"Puerto eliminado: {port_selection}")
    except Exception as e:
        print(f"Error al eliminar el puerto: {e}")
    finally:
        if not db.is_closed():
            db.close()
    
    dpg.delete_item("remove_ports_modal")

def create_node_and_close_modal():
    """Crea un nuevo nodo en la DB y cierra el modal."""
    node_name = dpg.get_value("new_node_name")
    node_type_name = dpg.get_value("new_node_type")
    
    if not node_name or not node_type_name:
        print("Error: Nombre o tipo de nodo no especificado.")
        return

    try:
        db.connect(reuse_if_open=True)
        with db.atomic():
            node_type = NodeType.get(NodeType.name == node_type_name)
            new_node = Node.create(name=node_name, node_type=node_type.id, pos_x=50, pos_y=50)
            # Crea puertos para evitar bug
            Port.create(node=new_node, port_name="Input 1", port_type=INPUT_DENOM)
            Port.create(node=new_node, port_name="Output 1", port_type=OUTPUT_DENOM)

        print(f"Nodo '{node_name}' creado con ID {new_node.id}.")
        
        # Añadir el nuevo nodo a la GUI
        node_label = f"[{node_type.name}] {new_node.name} - #{new_node.id}"
        with dpg.node(label=node_label, parent="node_editor", pos=[new_node.pos_x, new_node.pos_y], tag=f"node_{new_node.id}"):
            for port in new_node.ports.order_by(Port.port_type.desc()):
                attr_type = dpg.mvNode_Attr_Output if port.port_type == OUTPUT_DENOM else dpg.mvNode_Attr_Input
                with dpg.node_attribute(label=port.port_name, attribute_type=attr_type, tag=f"port_{port.id}"):
                    dpg.add_text(f"Port: {port.port_name}")

    except Exception as e:
        print(f"Error al crear el nodo: {e}")
    finally:
        if not db.is_closed():
            db.close()
    
    dpg.delete_item("add_node_modal")

def add_node_callback(sender, app_data):
    """Callback para añadir un nuevo nodo (placeholder)."""
    with dpg.window(label="Añadir Nodo", width=300, height=200, pos=[400, 200], modal=True, tag="add_node_modal"):
        dpg.add_input_text(label="Nombre del Nodo", tag="new_node_name")
        dpg.add_combo(label="Tipo de Nodo", items=[nt.name for nt in NodeType.select()], tag="new_node_type")
        dpg.add_button(label="Crear", callback=lambda s, a: create_node_and_close_modal())


def remove_node_callback(sender, app_data):
    """Callback para eliminar un nodo seleccionado (placeholder)."""
    select_nodes = dpg.get_selected_nodes(node_editor="node_editor")
    if not select_nodes:
        return
    with dpg.window(label="Eliminar Nodo", width=300, height=150, pos=[400, 200], modal=True, tag="remove_node_modal"):
        for n in select_nodes:
            dpg.add_text(f" Nodo seleccionado: {dpg.get_item_alias(n)}")
        dpg.add_text(f"¿Eliminar nodos seleccionados?")
        dpg.add_button(label="Confirmar", callback=lambda s, a: confirm_remove_nodes(select_nodes))
        dpg.add_button(label="Cancelar", callback=lambda s, a: dpg.delete_item("remove_node_modal"))

def add_ports_callback(sender, app_data):
    """Callback para configurar los puertos de un nodo seleccionado."""
    select_nodes = dpg.get_selected_nodes(node_editor="node_editor")
    if len(select_nodes) != 1:
        print("Seleccione un solo nodo para configurar.")
        return
    with dpg.window(label=f"Modificar Puertos para {dpg.get_item_alias(select_nodes[0])}", width=300, height=200, pos=[400, 200], modal=True, tag="add_ports_modal"):
        dpg.add_text("Añadir Nuevo Puerto")
        dpg.add_text(f"Nodo seleccionado: {dpg.get_item_alias(select_nodes[0])}", tag="node_select")
        dpg.add_input_text(label="Nombre del Puerto", tag="port_name")
        dpg.add_combo(label="Tipo de Puerto", items=[INPUT_DENOM, OUTPUT_DENOM], tag="port_type")
        dpg.add_button(label="Añadir Puerto", callback=lambda s, a: add_port_to_node())

def remove_ports_callback(sender, app_data):
    """Callback para eliminar puertos de un nodo seleccionado (placeholder)."""
    select_nodes = dpg.get_selected_nodes(node_editor="node_editor")
    if len(select_nodes) != 1:
        print("Seleccione un solo nodo para configurar.")
        return
    
    with dpg.window(label=f"Eliminar Puertos para {dpg.get_item_alias(select_nodes[0])}", width=300, height=200, pos=[400, 200], modal=True, tag="remove_ports_modal"):
        dpg.add_text(f"Nodo seleccionado: {dpg.get_item_alias(select_nodes[0])}", tag="port_rm_node_select")
        node_id = int(dpg.get_item_alias(select_nodes[0]).split('_')[-1])
        
        try:
            db.connect(reuse_if_open=True)
            node = Node.get_by_id(node_id)
            port_items = [f"{port.port_name} (ID: {port.id})" for port in node.ports]
        except Exception as e:
            print(f"Error al obtener puertos: {e}")
            port_items = []
        finally:
            if not db.is_closed():
                db.close()
        
        if not port_items:
            dpg.add_text("No hay puertos para eliminar.")
        else:
            dpg.add_combo(label="Seleccionar Puerto", items=port_items, tag="port_to_remove")
            dpg.add_button(label="Eliminar Puerto", callback=lambda s, a: confirm_remove_port())
        dpg.add_button(label="Cancelar", callback=lambda s, a: dpg.delete_item("remove_ports_modal"))

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
    from_port_tag, to_port_tag = dpg.get_item_alias(config["attr_1"]), dpg.get_item_alias(config["attr_2"])
    print(f"Conexión a eliminar: {from_port_tag} -> {to_port_tag}")
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

        with dpg.window(label="Controles", width=1800, height=50, pos=[0, 0]):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Guardar Posiciones", callback=save_node_positions)
                dpg.add_button(label="Commit Cambios", callback=lambda: print("Funcionalidad de commit no implementada aún."))

        with dpg.group(horizontal=True):
            with dpg.window(label="Nodos", width=1600, height=600, pos=[0, 50]):
                with dpg.node_editor(callback=link_callback, delink_callback=delink_callback, tag="node_editor"):
                    # Esta función llenará el editor con los datos de la DB
                    build_gui_from_db("node_editor")

            with dpg.window(label="Panel de Nodos", width=200, height=600, pos=[1610, 50]):
                dpg.add_button(label="Añadir Nodo", callback=add_node_callback)
                dpg.add_button(label="Eliminar Nodo", callback=remove_node_callback)
                dpg.add_button(label="Añadir Puertos", callback=add_ports_callback)
                dpg.add_button(label="Eliminar Puertos", callback=remove_ports_callback)

    dpg.create_viewport(title='Eunomia - Dossier de Accion', width=1800, height=800)
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
