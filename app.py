from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Azure AI Foundry Control Plane Demo Generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tui", help="Run the Textual terminal UI")

    web = sub.add_parser("web", help="Run the Gradio web UI")
    web.add_argument("--host", default=None, help="Server host (default: gradio default)")
    web.add_argument("--port", type=int, default=None, help="Server port (default: gradio default)")
    web.add_argument("--share", action="store_true", help="Enable gradio share link")

    args = parser.parse_args()

    if args.cmd == "tui":
        from foundry_demo.tui import main as tui_main

        tui_main()
        return 0

    if args.cmd == "web":
        from foundry_demo.webui import build_app

        app = build_app()
        app.launch(server_name=args.host, server_port=args.port, share=bool(args.share))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

