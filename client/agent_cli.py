import json

from mcp_adapter import BlenderMCPAdapter


def print_json(payload):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def help_payload():
    return {
        "commands": {
            "help": "Show CLI help.",
            "tools": "List available tools.",
            "quit": "Exit the CLI.",
            "raw <tool_name> <json_params>": "Call a tool directly with JSON params.",
        },
        "prompt_examples": [
            "scene info",
            "info de escena",
            "create a chair",
            "crea una mesa",
            "create punk character from references",
            "crea un personaje punk",
            "review character",
            "revisa el personaje",
            "fix proportions",
            "arregla proporciones",
            "create shop scene",
            "create bedroom blockout",
            "create street blockout",
        ],
    }


def main():
    adapter = BlenderMCPAdapter()
    tools = adapter.list_tools()

    print_json(
        {
            "status": "ready",
            "message": "Blender MCP agent CLI started",
            "tool_count": len(tools),
            "commands": ["help", "tools", "quit", "raw <tool_name> <json_params>"],
        }
    )
    print_json({"available_tools": [tool["name"] for tool in tools]})

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
            print_json({"tools": tools})
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
