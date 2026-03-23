import json

from mcp_adapter import BlenderMCPAdapter


def main():
    adapter = BlenderMCPAdapter()

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        try:
            call = adapter.route_prompt(user_input)
            result = adapter.call_tool(call["tool"], call["params"])
            print(json.dumps({"call": call, "result": result}, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
