import sqlite3
import json
import shutil
import datetime
from .persistance_api import MAIN_DB_PATH, STAGE_DB_PATH
global commit_MESSAGE
commit_MESSAGE = "No message"

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

def log_diff(diff: dict, msg:str, author: str = "admin", log_file: str = "commits.log"):
    """
    Escribe un log del diff con timestamp y autor en el archivo especificado.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    diff_str = stringify_changes(diff)
    diff_hash = hash(json.dumps(diff, sort_keys=True))
    log_entry = (
        f"---\nTimestamp: {timestamp}\nMessage: {msg}\nAuthor: {author}\nAdmin: {author}\nDiff:\n{diff_str}\nDiff Hash: {diff_hash}\n\n"
    )
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def commit_changes_to_db(msg):
    """Genera diff, muestra y si todo ok, reemplaza main db con staging."""
    diff = generate_diff()
 
    print(stringify_changes(diff))

    user_ok = True  
    if not user_ok:
        print("Commit cancelado.")
        return

    shutil.copyfile(STAGE_DB_PATH, MAIN_DB_PATH)
    print(f"Commit aplicado. {MAIN_DB_PATH} actualizado.")
    log_diff(diff, msg)

def get_commits(log_file: str = "commits.log") -> list:
    """Lee el archivo de log y devuelve una lista de commits como dicts."""
    commits = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return commits

    raw_commits = content.strip().split("---\n")
    for entry in raw_commits:
        if not entry.strip():
            continue
        lines = entry.strip().split("\n")
        commit = {}

        for line in lines:
            if line.startswith("Timestamp:"):
                commit["timestamp"] = line.split(":", 1)[1].strip()
            elif line.startswith("Message:"):
                commit["message"] = line.split(":", 1)[1].strip()
            elif line.startswith("Author:"):
                commit["author"] = line.split(":", 1)[1].strip()
            elif line.startswith("Admin:"):
                commit["admin"] = line.split(":", 1)[1].strip()
            elif line.startswith("Diff Hash:"):
                commit["diff_hash"] = line.split(":", 1)[1].strip()
        commits.append(commit)
    return commits
