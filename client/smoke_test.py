import json
import sys

from blender_client import BlenderTcpClient


CHECK_OBJECT_INFO_FLAG = "--check-object-info"
WITH_CHARACTER_FLAG = "--with-character"


def run_step(name, func):
    print(f"[RUN ] {name}")
    try:
        result = func()
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        raise
    print(f"[PASS] {name}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main() -> int:
    client = BlenderTcpClient.from_env()
    check_object_info = CHECK_OBJECT_INFO_FLAG in sys.argv
    with_character = WITH_CHARACTER_FLAG in sys.argv
    print(
        "Smoke test target:",
        json.dumps(
            {
                "host": client.host,
                "port": client.port,
                "timeout_seconds": client.timeout_seconds,
            },
            ensure_ascii=False,
        ),
    )

    try:
        run_step("get_scene_info", lambda: client.call("get_scene_info"))
        run_step(
            "create_prop_blockout",
            lambda: client.call(
                "create_prop_blockout",
                {
                    "mode": "props",
                    "prop_type": "table",
                    "collection_name": "MCP_SmokeTest_Props",
                },
            ),
        )
        if check_object_info:
            run_step(
                "get_object_info",
                lambda: client.call(
                    "get_object_info",
                    {
                        "name": "PROP_Table_Top",
                    },
                ),
            )

        if with_character:
            run_step(
                "create_character_blockout",
                lambda: client.call(
                    "create_character_blockout",
                    {
                        "mode": "character",
                        "height": 1.8,
                        "collection_name": "MCP_SmokeTest_Character",
                    },
                ),
            )
    except Exception:
        return 1

    enabled_flags = {
        "check_object_info": check_object_info,
        "with_character": with_character,
    }
    print("[DONE] Smoke test passed")
    print(json.dumps({"options": enabled_flags}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
