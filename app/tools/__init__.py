from typing import Any, Callable

_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict,
    handler: Callable[..., str],
):
    _REGISTRY[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "handler": handler,
    }


def get_tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in _REGISTRY.values()
    ]


def execute_tool(name: str, arguments: dict) -> str:
    tool = _REGISTRY.get(name)
    if not tool:
        return f"Fehler: Werkzeug '{name}' nicht gefunden."
    try:
        return tool["handler"](**arguments)
    except Exception as e:
        return f"Fehler bei {name}: {e}"


def get_available_tool_names() -> list[str]:
    return list(_REGISTRY.keys())
