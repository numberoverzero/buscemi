import re
from typing import Any, Iterable, List, Optional, Tuple


missing = object()

OPTION_RE = re.compile(
    """^
        option\s+
        name\s+
          (?P<name>.+?)\s+
        type\s+
          (?P<type>.+?)\s+
        default\s*
          (?P<default>.+)?
    $""",
    re.MULTILINE | re.VERBOSE
)

INT_RE = re.compile(
    """^
        (?P<default>-?\d+)\s+
        min\s+
          (?P<min>-?\d+)\s+
        max\s+
          (?P<max>-?\d+)
    $""",
    re.MULTILINE | re.VERBOSE
)


def extract_option(line: str) -> Optional[dict]:
    """
    Sample values for recognized types::

        option name Contempt type spin default 24 min -100 max 100
            {
                "name": "Contempt",
                "type": "int",
                "default": 24,
                "min": -100,
                "max": 100
            }

        option name Analysis Contempt type combo default Both var Off var White var Black var Both
            {
                "name": "Analysis Contempt",
                "type": "enum",
                "default": "Both",
                "values": ["Off", "White", "Black", "Both"]
            }

        option name Debug Log File type string default
            {
                "name": "Debug Log File",
                "type": "string",
                "default": ""
            }

        option name Clear Hash type button
            {
                "name": "Clear Hash",
                "type": "func",
                "default": None,
            }

        option name Ponder type check default false
            {
                "name": "Ponder",
                "type": "bool",
                "default": False
            }
    """
    d = OPTION_RE.match(line)
    if not d:
        return None
    d = d.groupdict()

    type = {
        "string": "str",
        "spin": "int",
        "combo": "enum",
        "button": "func",
        "check": "bool",
    }[d["type"]]
    default = d["default"]

    opt = {
        "name": d["name"],
        "type": type,
    }

    if type == "str":
        opt["default"] = default
    elif type == "int":
        m = INT_RE.match(default)
        if m is None:
            raise ValueError(f"malformed default for spin {default!r}")
        g = m.groupdict()
        for k in {"min", "max", "default"}:
            opt[k] = int(g[k])
    elif type == "enum":
        values = [x.strip() for x in default.split("var")]
        opt["default"] = values[0]
        opt["values"] = {x.lower(): x for x in values[1:]}
    elif type == "func":
        opt["default"] = None
    elif type == "bool":
        opt["default"] = default == "true"

    return opt


def format_set_option(opt: dict, value: Any=missing) -> Tuple[str, Optional[str]]:
    """
    {"name: "Ponder", "type": "bool", "default": True}, missing -> ("Ponder", "true")
    """
    name = opt["name"]
    type = opt["type"]
    if value is missing:
        value = opt["default"]

    if type == "func":
        if value is not None:
            raise ValueError(f"option {name} does not support a value {value!r}")
    elif type == "bool":
        value = {
            True: "true",
            False: "false"
        }[bool(value)]
    elif type == "enum":
        allowed = opt["values"]
        if value.lower() not in allowed.keys():
            raise ValueError(f"value {value!r} not one of {allowed.values()}")
        value = opt["values"][value.lower()]
    elif type == "int":
        min, max = opt["min"], opt["max"]
        if value < min or value > max:
            raise ValueError(f"value {value!r} not within range [{min}, {max}]")
    return name, value


def format_go_arguments(
        searchmoves: Iterable[str] = None, ponder: bool = False,
        wtime: int = None, btime: int = None, winc: int = None, binc: int = None,
        movestogo: int = None, depth: int = None, nodes: int = None, mate: int = None, movetime: int = None,
        infinite: bool = False
) -> List[str]:
    args = []

    def _set(name: str, field: Any):
        if field is not None:
            args.append(name)
            args.append(str(field))

    _set("wtime", wtime)
    _set("btime", btime)
    _set("winc", winc)
    _set("binc", binc)
    _set("movestogo", movestogo)

    _set("depth", depth)
    _set("nodes", nodes)
    _set("mate", mate)

    _set("movetime", movetime)

    if ponder:
        args.append("ponder")

    if infinite:
        args.append("infinite")

    if searchmoves:
        args.append("searchmoves")
        args.extend(searchmoves)

    return args
