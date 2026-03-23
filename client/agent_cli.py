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
        "examples": [
            "create punk character from references",
            "create shop scene",
            "create bedroom blockout",
            "review character",
            "raw get_scene_info {}",
        ],
    }


def main():
    adapter = BlenderMCPAdapter()

    print_json(
        {
            "status": "ready",
            "message": "Blender MCP agent CLI started",
            "tool_count": len(adapter.list_tools()),
            "commands": ["help", "tools", "quit", "raw <tool_name> <json_params>"],
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
            print_json({"tools": adapter.list_tools()})
            continue

        try:
            if user_input.startswith("raw "):
                parts = user_input.split(" ", 2)
                if len(parts) != 3:
                    raise ValueError("raw command format: raw <tool_name> <json_params>")
                tool_name = parts[1]
                params = json.loads(parts[2])
                result = adapter.call_tool(tool_name, params)
                print_json({"tool": tool_name, "params": params, "result": result})
                continue

            call = adapter.route_prompt(user_input)
            result = adapter.call_tool(call["tool"], call["params"])
            print_json({"prompt": user_input, "call": call, "result": result})
        except Exception as exc:
            print_json({"error": str(exc)})


if __name__ == "__main__":
    main()
