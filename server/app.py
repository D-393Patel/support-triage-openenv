"""Compatibility FastAPI entrypoint expected by OpenEnv validators."""

from support_triage_env.server.app import app as app
from support_triage_env.server.app import main as _support_main


def main() -> None:
    _support_main()


if __name__ == "__main__":
    main()
