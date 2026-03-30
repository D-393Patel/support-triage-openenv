"""FastAPI app entrypoint for the support triage environment."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

try:
    from openenv.core.env_server import HTTPEnvServer, create_web_interface_app
except ImportError:
    from openenv.core.env_server import HTTPEnvServer
    create_web_interface_app = None

from support_triage_env.models import SupportTriageAction, SupportTriageObservation
from support_triage_env.server.environment import SupportTriageEnvironment


def create_environment() -> SupportTriageEnvironment:
    task_id = os.getenv("SUPPORT_TRIAGE_TASK_ID")
    return SupportTriageEnvironment(task_id=task_id)


if create_web_interface_app is not None:
    app = create_web_interface_app(
        create_environment,
        SupportTriageAction,
        SupportTriageObservation,
        env_name="support_triage_env",
    )
else:
    app = FastAPI(title="support_triage_env")
    server = HTTPEnvServer(
        env=create_environment,
        action_cls=SupportTriageAction,
        observation_cls=SupportTriageObservation,
    )
    server.register_routes(app)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    main()
