from __future__ import annotations

import argparse

import uvicorn

from .config import load_config
from .main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SkyLedger dashboard server.")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Override dashboard port")
    args = parser.parse_args()

    config = load_config(args.config)
    uvicorn.run(
        create_app(args.config),
        host=args.host,
        port=args.port or config.dashboard_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
