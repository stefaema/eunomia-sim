import dearpygui.dearpygui as dpg


dpg.create_context()

def link_callback(sender, app_data):
    dpg.add_node_link(app_data[0], app_data[1], parent=sender)

def delink_callback(sender, app_data):
    dpg.delete_item(app_data)

with dpg.window(label="Eunomia - Dossier de Accion", tag="Primary Window"):
    dpg.add_text("Dossier de Acción")
    with dpg.node_editor(callback=link_callback, delink_callback=delink_callback):
        with dpg.node(label="Node 1"):
            with dpg.node_attribute(label="Node A1"):
                dpg.add_input_float(label="F1", width=150)

            with dpg.node_attribute(label="Node A2", attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_input_float(label="F2", width=150)

        with dpg.node(label="Node 2"):
            with dpg.node_attribute(label="Node A3"):
                dpg.add_input_float(label="F3", width=200)

            with dpg.node_attribute(label="Node A4", attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_input_float(label="F4", width=200)

dpg.create_viewport(title='Eunomoia - Dossier de Accion', width=800, height=800)
dpg.setup_dearpygui() 


dpg.show_item_registry()
dpg.show_debug()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)
dpg.start_dearpygui() # Handles rendering and event loop
dpg.destroy_context()
