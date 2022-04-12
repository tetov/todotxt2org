import sys
from pathlib import Path
from datetime import date
import re

import todotxtio
import importlib.util

REPO_DIR = Path(__file__).parent.parent


def load_inorganic():
    """Load non packaged inorganic.

    https://stackoverflow.com/a/41595552
    """
    modname = "inorganic"
    fname = REPO_DIR / "vendor/inorganic/src/inorganic.py"
    spec = importlib.util.spec_from_file_location(modname, fname)
    if spec is None:
        raise ImportError(f"Could not load spec for module '{modname}' at: {fname}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    try:
        spec.loader.exec_module(module)
    except FileNotFoundError as e:
        raise ImportError(f"{e.strerror}: {fname}") from e

    return module


def todotxtio_to_orgparse(todotxtio_todos, todotxt_raw):
    inorganic = load_inorganic()
    inOrgNode = inorganic.OrgNode
    asorgdate = inorganic.asorgdate

    org_nodes = []

    def datestr_to_orgdate(datestr):
        date_obj = date.fromisoformat(datestr.strip())
        return asorgdate(date_obj)

    for todo, raw_line in zip(todotxtio_todos, todotxt_raw, strict=True):
        raw_line = raw_line.strip()
        dict_ = todo.to_dict()
        print(dict_)

        todo_done = dict_["completed"]
        todo_projects = dict_.get("projects") or []
        todo_contexts = dict_.get("contexts") or []
        todo_tags = dict_.get("tags") or {}

        # TODO: pri is not getting picked up as a tag
        todo_priority = dict_.get("priority") or todo_tags.get("pri")

        todo_due_date = todo_tags.get("due")
        todo_threshold_datestr = todo_tags.get("t")
        todo_completion_date = dict_.get("completion_date")

        org_headline = dict_["text"]

        if todo_priority:
            org_prio = f"[#{todo_priority.upper()}] "
            org_headline = org_prio + org_headline

        # work around bug where creation date is ignored for non completed todos
        # with prio
        if todo_priority and not todo_done:
            dates = re.findall(
                r"(\s([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9]))", raw_line
            )
            if len(dates) == 1:
                todo_creation_date = dates[0][0].strip()
            elif len(dates) > 1:
                raise RuntimeError(f"More than one date found in {raw_line}")
            else:
                print("No match")
                todo_creation_date = None
        else:
            todo_creation_date = dict_.get("creation_date")

        org_body = ""

        if todo_completion_date:
            org_body += f"DONE: [{datestr_to_orgdate(todo_creation_date)}]\n"

        if todo_creation_date:
            org_body += f"[{datestr_to_orgdate(todo_creation_date)}]\n"

        if todo_due_date:
            org_body += f"DEADLINE: <{datestr_to_orgdate(todo_creation_date)}>\n"

        org_properties = {"Imported todo.txt line": raw_line.strip()}

        if todo_contexts:
            org_properties["todotxt_contexts"] = todo_contexts

        org_todo = "DONE" if todo_done else "TODO"

        org_scheduled = (
            date.fromisoformat(todo_threshold_datestr)
            if todo_threshold_datestr
            else None
        )

        orgnode = inOrgNode(
            org_headline,
            todo=org_todo,
            tags=todo_projects,
            properties=org_properties,
            scheduled=org_scheduled,
            body=org_body if len(org_body) > 0 else None,
        )
        print(orgnode)
        print(orgnode.render())
        print("\n")

        org_nodes.append(orgnode)

    return org_nodes


def get_lines(path: Path):
    with path.open(mode="r") as fp:
        return fp.readlines()


def write_nodes_to_files(nodes, file_):
    with file_.open(mode="w") as fp:
        for node in nodes:
            fp.write(node.render())


if __name__ == "__main__":
    todotxt_dir = Path.home() / "Dropbox" / "todo"
    todotxt_file = todotxt_dir / "todo.txt"

    org_dir = Path.home() / "Dropbox" / "org"
    org_file = org_dir / "todotxt_import.org"

    todotxt_raw = get_lines(todotxt_file)

    todotxtio_todos = todotxtio.from_file(str(todotxt_file))
    orgnodes = todotxtio_to_orgparse(todotxtio_todos, todotxt_raw)

    write_nodes_to_files(orgnodes, org_file)
