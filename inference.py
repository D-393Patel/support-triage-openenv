"""Baseline inference for the support triage OpenEnv environment."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI
from openai import APIError

from support_triage_env.models import SupportTriageAction, SupportTriageObservation
from support_triage_env.server.environment import SupportTriageEnvironment
from support_triage_env.tasks import TASKS

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
OUTPUT_PATH = Path("outputs/evals/baseline_scores.json")
TEMPERATURE = 0.0
MAX_TOKENS = 300
MAX_RETRIES = 3

SYSTEM_PROMPT = """You are triaging a support queue.
Return exactly one compact JSON object with this schema:
{"operation":"inspect_ticket|set_priority|assign_team|add_tag|send_reply|resolve_ticket|submit","ticket_id":"optional","value":"optional","message":"optional"}
Rules:
- Use only operations listed in the observation.
- Inspect before making irreversible choices when context is incomplete.
- Do not invent ticket ids.
- When the queue looks complete, return {"operation":"submit"}.
- Return JSON only, with double quotes.
"""


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str, value: str | None) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def observation_payload(observation: SupportTriageObservation) -> Dict[str, Any]:
    return observation.model_dump(mode="json", exclude_none=True)


def parse_action(raw_text: str, observation: SupportTriageObservation) -> SupportTriageAction:
    try:
        data = json.loads(raw_text)
        return SupportTriageAction.model_validate(data)
    except Exception:
        return heuristic_action(observation)


def heuristic_action(observation: SupportTriageObservation) -> SupportTriageAction:
    for ticket in observation.tickets:
        if not ticket.visible_context:
            return SupportTriageAction(operation="inspect_ticket", ticket_id=ticket.ticket_id)

    for ticket in observation.tickets:
        text = " ".join(
            [ticket.subject, ticket.summary, " ".join(ticket.visible_context)]
        ).lower()

        if ticket.current_priority is None:
            if "outage" in text or "compromise" in text or "mfa" in text:
                return SupportTriageAction(
                    operation="set_priority", ticket_id=ticket.ticket_id, value="urgent"
                )
            if "gdpr" in text or "duplicate charge" in text or "charged twice" in text:
                return SupportTriageAction(
                    operation="set_priority", ticket_id=ticket.ticket_id, value="high"
                )
            return SupportTriageAction(
                operation="set_priority", ticket_id=ticket.ticket_id, value="low"
            )

        if ticket.current_team is None:
            if "billing" in text or "invoice" in text or "refund" in text or "charge" in text:
                team = "billing"
            elif "gdpr" in text or "personal data" in text:
                team = "compliance"
            elif "outage" in text or "api" in text:
                team = "engineering"
            elif "mfa" in text or "compromise" in text or "security" in text:
                team = "security"
            else:
                team = "product"
            return SupportTriageAction(
                operation="assign_team", ticket_id=ticket.ticket_id, value=team
            )

        expected_tags = {
            "refund": ["refund", "duplicate-charge"],
            "invoice": ["invoice"],
            "security": ["account-takeover", "verification"],
            "outage": ["outage", "vip", "sla-risk"],
            "gdpr": ["gdpr", "data-deletion"],
            "feature": ["feature-request"],
        }
        for keyword, tags in expected_tags.items():
            if keyword in text:
                for tag in tags:
                    if tag not in ticket.tags:
                        return SupportTriageAction(
                            operation="add_tag", ticket_id=ticket.ticket_id, value=tag
                        )

        if ticket.last_reply is None:
            if "refund" in text or "charge" in text:
                message = (
                    "We have approved the refund for the duplicate charge. Sorry for the trouble. "
                    "You will see it in 3-5 business days."
                )
            elif "invoice" in text:
                message = "Your VAT invoice is available now and has been sent to you."
            elif "mfa" in text or "compromise" in text:
                message = (
                    "We are treating this as an account security issue. Please verify your identity "
                    "so we can secure the account and continue recovery."
                )
            elif "gdpr" in text or "personal data" in text:
                message = (
                    "We can process the delete request once we verify identity. GDPR deletion is "
                    "completed within 30 days after verification."
                )
            elif "outage" in text:
                message = (
                    "We have opened an incident with engineering and will share updates as we work "
                    "through mitigation."
                )
            else:
                message = "Thanks for the feedback. We have forwarded it to the product team."
            return SupportTriageAction(
                operation="send_reply", ticket_id=ticket.ticket_id, message=message
            )

        if ticket.current_status != "resolved" and (
            "refund" in text
            or "invoice" in text
            or "feature request" in text
            or "dark mode" in text
        ):
            resolution = "refund_approved"
            if "invoice" in text:
                resolution = "invoice_sent"
            if "feature request" in text or "dark mode" in text:
                resolution = "forwarded_to_product"
            return SupportTriageAction(
                operation="resolve_ticket", ticket_id=ticket.ticket_id, value=resolution
            )

    return SupportTriageAction(operation="submit")


def ask_model(
    client: OpenAI | None,
    observation: SupportTriageObservation,
    history: List[Dict[str, Any]],
) -> SupportTriageAction:
    if client is None or not MODEL_NAME:
        return heuristic_action(observation)

    payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "observation": observation_payload(observation),
                    "recent_actions": history[-6:],
                },
                indent=2,
            ),
        },
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=require_env("MODEL_NAME", MODEL_NAME),
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                messages=payload,
            )
            raw_text = response.choices[0].message.content or ""
            return parse_action(raw_text, observation)
        except APIError as exc:
            if attempt == MAX_RETRIES:
                print(
                    f"Model request failed after {MAX_RETRIES} attempts ({exc}). "
                    "Falling back to the heuristic policy."
                )
                return heuristic_action(observation)
            time.sleep(attempt)

    return heuristic_action(observation)


def run_task(client: OpenAI | None, task_id: str) -> Dict[str, Any]:
    env = SupportTriageEnvironment(task_id=task_id)
    observation = env.reset(episode_id=f"baseline-{task_id}")
    history: List[Dict[str, Any]] = []

    while True:
        action = ask_model(client, observation, history)
        result = env.step(action)
        history.append(
            {
                "action": action.model_dump(exclude_none=True),
                "reward": result.reward,
                "score": result.current_score,
                "done": result.done,
                "last_result": result.last_result,
            }
        )
        observation = result
        if result.done:
            break

    return {
        "task_id": task_id,
        "score": observation.current_score,
        "steps": env.state.step_count,
        "history": history,
    }


def main() -> None:
    if os.getenv("LOAD_DOTENV", "1") != "0":
        load_dotenv()
    global API_BASE_URL, API_KEY, MODEL_NAME
    API_BASE_URL = os.getenv("API_BASE_URL") or API_BASE_URL
    API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or API_KEY
    MODEL_NAME = os.getenv("MODEL_NAME") or MODEL_NAME

    client: OpenAI | None = None
    run_mode = "heuristic"
    if API_KEY and MODEL_NAME:
        client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
        )
        run_mode = "model_with_heuristic_fallback"
    else:
        print(
            "No API key or MODEL_NAME configured. Running the deterministic heuristic baseline."
        )

    results = [run_task(client, task.task_id) for task in TASKS]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": run_mode,
        "model": MODEL_NAME or "heuristic-only",
        "api_base_url": API_BASE_URL,
        "results": results,
        "average_score": round(
            sum(item["score"] for item in results) / max(len(results), 1), 4
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
