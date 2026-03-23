import json

from mcp_adapter import BlenderMCPAdapter
from tools_registry import CALLABLE_TOOLS


def print_json(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def help_payload():
    return {
        "commands": {
            "help": "Show CLI help.",
            "tools": "List callable MCP tools, including safe workflow helpers.",
            "quit": "Exit the CLI.",
            "raw <tool_name> <json_params>": "Call a tool directly with JSON params.",
        },
        "prompt_examples": [
            "scene info",
            "info de escena",
            "create a chair in Blender",
            "crea una mesa",
            "crea una silla en Blender",
            "create punk character",
            "crea un personaje punk",
            "review character",
            "revisa el personaje",
            "fix proportions",
            "arregla proporciones",
            "create shop scene",
            "create a stylized bedroom with sunset lighting",
            "crea una habitación low poly con cama, escritorio y lámpara",
            "create bedroom blockout",
            "create street blockout",
        ],
    }


def main():
    adapter = BlenderMCPAdapter()
    tools = adapter.list_tools()
    callable_tools = [tool["name"] for tool in CALLABLE_TOOLS]

    print_json(
        {
            "status": "ready",
            "message": "Blender MCP agent CLI started",
            "tool_count": len(callable_tools),
            "commands": ["help", "tools", "quit", "raw <tool_name> <json_params>"],
        }
    )
    print_json(
        {
            "callable_mcp_tools": callable_tools,
            "prompt_helpers": [
                "create punk character",
                "crea un personaje punk",
                "create shop scene",
                "create a stylized bedroom with sunset lighting",
                "review character",
                "revisa el personaje",
            ],
        }
    )

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        lowered = user_input.lower()
        if lowered == "quit":
            break
        if lowered == "help":
            print_json(help_payload())
            continue
        if lowered == "tools":
            print_json({"tools": [tool for tool in tools if tool["availability"] in {"server", "workflow"}]})
            continue

        try:
            if user_input.startswith("raw "):
                parts = user_input.split(" ", 2)
                if len(parts) != 3:
                    raise ValueError("raw command format: raw <tool_name> <json_params>")
                tool_name = parts[1]
                params = json.loads(parts[2])
                result = adapter.call_tool(tool_name, params)
                print_json(
                    {
                        "mode": "raw",
                        "tool": tool_name,
                        "params": params,
                        "result": result,
                    }
                )
                continue

            route = adapter.route_prompt(user_input)
            print_json({"mode": "routed", "prompt": user_input, "route": route})
            if "error" in route:
                continue

            result = adapter.call_tool(route["tool"], route["params"])
            print_json({"tool": route["tool"], "params": route["params"], "result": result})
        except Exception as exc:
            print_json({"error": str(exc)})


if __name__ == "__main__":
    main()
