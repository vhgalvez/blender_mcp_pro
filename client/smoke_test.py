import json
import sys

from blender_client import BlenderTcpClient


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

        if "--with-character" in sys.argv:
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

    print("[DONE] Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
