import sqlite3
import json
import shutil
from .persistance_api import MAIN_DB_PATH, STAGE_DB_PATH

def _table_to_dict(conn, table):
    """Devuelve un dict {id: tuple_campos} para la tabla dada."""
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    return {row[0]: row for row in rows}  # asume id en col 0


def generate_diff():
    """Compara la DB principal y la staging y devuelve dict con cambios."""
    changes = {}
    with sqlite3.connect(MAIN_DB_PATH) as old, sqlite3.connect(STAGE_DB_PATH) as new:
        for table in ("node", "port", "connection", "portparameter", "nodecallback"):
            old_rows = _table_to_dict(old, table)
            new_rows = _table_to_dict(new, table)
            added = [new_rows[k] for k in new_rows.keys() - old_rows.keys()]
            removed = [old_rows[k] for k in old_rows.keys() - new_rows.keys()]
            modified = []
            for k in new_rows.keys() & old_rows.keys():
                if new_rows[k] != old_rows[k]:
                    modified.append({"before": old_rows[k], "after": new_rows[k]})
            changes[table] = {
                "added": added,
                "removed": removed,
                "modified": modified,
            }
    return changes

def stringify_changes(diff: dict) -> str:
    """
    Convierte el dict de cambios generado por generate_diff() en un string legible.
    """
    lines = []
    for table, c in diff.items():
        added, removed, modified = c["added"], c["removed"], c["modified"]
        if not (added or removed or modified):
            continue
        lines.append(f"=== {table.upper()} ===")
        if added:
            lines.append(f"  +{len(added)} agregados:")
            for row in added:
                lines.append(f"    + {row}")
        if removed:
            lines.append(f"  -{len(removed)} eliminados:")
            for row in removed:
                lines.append(f"    - {row}")
        if modified:
            lines.append(f"  ~{len(modified)} modificados:")
            for m in modified:
                before = m["before"]
                after = m["after"]
                lines.append(f"    ~ antes: {before}")
                lines.append(f"      después: {after}")
    if not lines:
        return "Sin cambios detectados."
    return "\n".join(lines)


def commit_changes_to_db():
    """Genera diff, muestra y si todo ok, reemplaza main db con staging."""
    diff = generate_diff()
    # Mostrar diff en consola o GUI
    # Aquí podrías pedir confirmación al usuario (ej. un popup en DearPyGui)
    user_ok = True  # placeholder: integrar UI real
    if not user_ok:
        print("Commit cancelado.")
        return

    # Reemplazar base principal
    shutil.copyfile(STAGE_DB_PATH, MAIN_DB_PATH)
    print(f"Commit aplicado. {MAIN_DB_PATH} actualizado.")
