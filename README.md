# Support Triage OpenEnv

`support_triage_env` is a real-world OpenEnv environment that simulates customer support ticket triage. The agent must inspect tickets, route them to the correct team, set priority, add operational tags, send customer-facing replies, and decide whether it is safe to resolve the ticket.

The domain is useful for training and evaluation because support operations require structured decision-making under time pressure, clear policy compliance, and tradeoffs across multiple simultaneous tasks.

## Why this environment

- It models work that humans actually do in SaaS support teams.
- It supports dense rewards through partial credit on routing, prioritization, tagging, replies, and closure decisions.
- It exposes deterministic graders, so success is reproducible and hard to game.
- It includes increasing difficulty from a single billing ticket to a multi-queue enterprise workload.

## Tasks

1. `billing_refund_easy`
   Single duplicate-charge refund ticket. The agent must inspect the ticket, route it to billing, tag it correctly, communicate the refund timeline, and resolve it safely.
2. `account_security_medium`
   Two-ticket queue mixing a suspected account takeover with a routine invoice request. The agent must keep the security case open while resolving the invoice task.
3. `sla_multiqueue_hard`
   Three-ticket queue covering an enterprise outage, a GDPR deletion request, and a product feature request. The agent must protect an SLA-sensitive incident, route compliance work correctly, and only resolve the feature request.

## Action space

The environment uses a typed `SupportTriageAction` model with these operations:

- `inspect_ticket`
- `set_priority`
- `assign_team`
- `add_tag`
- `send_reply`
- `resolve_ticket`
- `submit`

Action payload:

```json
{
  "operation": "assign_team",
  "ticket_id": "T-300",
  "value": "engineering"
}
```

## Observation space

Each `SupportTriageObservation` includes:

- `task`: task metadata, objective, and difficulty
- `tickets`: ticket snapshots with current routing state, tags, reply text, SLA clock, and any revealed internal context
- `allowed_operations`: valid action list
- `last_result`: natural-language effect of the previous action
- `remaining_steps`: episode budget
- `current_score`: current deterministic grader score in `[0.0, 1.0]`
- `grader_breakdown`: per-ticket numeric progress signals without exposing hidden grader hints

## Reward design

The reward is shaped as:

`delta(grader_score) - action_cost + final_score_bonus_on_submit`

This gives positive signal for partial progress, a small per-step penalty to discourage wandering, and a larger penalty for invalid actions.

## Project structure

- [support_triage_env/tasks.py](C:\Users\Slim-5\OneDrive\Desktop\Project\support_triage_env\tasks.py): deterministic task seeds and grader targets
- [support_triage_env/graders.py](C:\Users\Slim-5\OneDrive\Desktop\Project\support_triage_env\graders.py): ticket-level and task-level scoring
- [support_triage_env/server/environment.py](C:\Users\Slim-5\OneDrive\Desktop\Project\support_triage_env\server\environment.py): environment logic implementing `reset()`, `step()`, and `state`
- [support_triage_env/server/app.py](C:\Users\Slim-5\OneDrive\Desktop\Project\support_triage_env\server\app.py): FastAPI/OpenEnv server
- [inference.py](C:\Users\Slim-5\OneDrive\Desktop\Project\inference.py): reproducible baseline runner using the OpenAI client

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Local usage

Run the server:

```bash
uvicorn support_triage_env.server.app:app --host 0.0.0.0 --port 8000
```

Run validation:

```bash
openenv validate
./scripts/validate-submission.sh https://your-space.hf.space .
```

Run the baseline with an external model if credentials are available:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="your-model"
export API_KEY="your-provider-key"
python inference.py
```

Run the baseline with no external API access:

```bash
LOAD_DOTENV=0 API_KEY= HF_TOKEN= OPENAI_API_KEY= MODEL_NAME=
python inference.py
```

In no-token mode, the script automatically runs a deterministic heuristic fallback baseline instead of failing.

Baseline output is written to `outputs/evals/baseline_scores.json`.

## Docker

Build and run locally:

```bash
docker build -t support-triage-env .
docker run --rm -p 8000:8000 support-triage-env
```

## Hugging Face Space notes

- Use Docker SDK for the Space.
- Tag the Space with `openenv`.
- Expose port `8000`.
- Optional: set `API_BASE_URL`, `MODEL_NAME`, and `API_KEY` in the environment if you want model-backed inference.
- The included baseline also works without any external API credentials by falling back to a deterministic heuristic policy.

## Baseline scores

Current local baseline artifact:

- Mode: model with heuristic fallback
- Average score: `0.9148`
- Output file: [baseline_scores.json](C:\Users\Slim-5\OneDrive\Desktop\Project\outputs\evals\baseline_scores.json)

The baseline runner is intentionally resilient: if model credentials are absent or provider credits are exhausted, it still completes successfully using the deterministic heuristic policy.
