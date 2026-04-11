"""Environment logic for support ticket triage."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from support_triage_env.graders import grade_task
from support_triage_env.models import (
    GraderBreakdown,
    SupportTriageAction,
    SupportTriageObservation,
    TaskCard,
    TicketView,
)
from support_triage_env.tasks import TASK_LOOKUP, TASKS, TaskSpec


VALID_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_TEAMS = {"billing", "security", "engineering", "compliance", "product", "general"}


class SupportTriageEnvironment(Environment):
    """A deterministic support queue simulation for agent training."""

    def __init__(self, task_id: Optional[str] = None):
        self._task_index = 0
        self._configured_task_id = task_id
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task: TaskSpec | None = None
        self._tickets: Dict[str, TicketView] = {}
        self._last_result = "Environment initialized."
        self._max_steps = 0
        self._score = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SupportTriageObservation:
        del seed, kwargs
        task_id = self._configured_task_id
        if not task_id:
            task = TASKS[self._task_index % len(TASKS)]
            self._task_index += 1
        else:
            task = TASK_LOOKUP[task_id]

        self._task = task
        self._max_steps = task.max_steps
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._tickets = {}
        self._last_result = (
            f"Loaded task {task.task_id}. Inspect tickets to reveal private operating context."
        )

        for seed_ticket in task.tickets:
            expectation = task.expectations[seed_ticket.ticket_id]
            self._tickets[seed_ticket.ticket_id] = TicketView(
                ticket_id=seed_ticket.ticket_id,
                customer_tier=seed_ticket.customer_tier,
                subject=seed_ticket.subject,
                channel=seed_ticket.channel,
                summary=seed_ticket.summary,
                current_status="open",
                tags=[],
                visible_context=[],
                sla_minutes_remaining=seed_ticket.sla_minutes_remaining,
                metadata={
                    "hidden_context": list(seed_ticket.hidden_context),
                    "inspected": False,
                    "acted_before_inspect": False,
                    "safety_breach": False,
                    "sla_breach": False,
                    "first_correct_priority_step": None,
                    "first_correct_team_step": None,
                    "expect_open": expectation.status == "open",
                },
            )

        breakdown = self._grade()
        self._score = breakdown.overall_score
        return self._observation(done=False, reward=0.0, breakdown=breakdown)

    def step(self, action: SupportTriageAction) -> SupportTriageObservation:
        if self._task is None:
            return self.reset()

        self._state.step_count += 1
        previous_score = self._score
        reward_penalty = -0.01
        done = False

        try:
            if action.operation == "submit":
                self._last_result = "Submission received. Final grader score calculated."
                done = True
            else:
                self._apply_action(action)
        except ValueError as exc:
            reward_penalty = -0.08
            self._last_result = str(exc)

        self._update_dynamics()

        if self._state.step_count >= self._max_steps:
            done = True
            self._last_result = f"{self._last_result} Episode ended due to step limit."

        breakdown = self._grade()
        self._score = breakdown.overall_score
        reward = round((self._score - previous_score) + reward_penalty, 4)
        if done:
            reward = round(reward + self._score, 4)
        return self._observation(done=done, reward=reward, breakdown=breakdown)

    @property
    def state(self) -> State:
        return self._state

    def _apply_action(self, action: SupportTriageAction) -> None:
        if not action.ticket_id:
            raise ValueError("ticket_id is required for this operation.")

        ticket = self._tickets.get(action.ticket_id)
        if ticket is None:
            raise ValueError(f"Unknown ticket_id: {action.ticket_id}")
        assert self._task is not None
        expectation = self._task.expectations[action.ticket_id]
        metadata = deepcopy(ticket.metadata or {})

        if action.operation != "inspect_ticket" and expectation.must_inspect and not metadata.get("inspected"):
            metadata["acted_before_inspect"] = True

        if action.operation == "inspect_ticket":
            hidden_context = list(metadata.get("hidden_context", []))
            ticket.visible_context = hidden_context
            metadata["inspected"] = True
            ticket.metadata = metadata
            self._last_result = f"Inspected {ticket.ticket_id} and revealed internal policy notes."
            return

        if action.operation == "set_priority":
            value = (action.value or "").lower()
            if value not in VALID_PRIORITIES:
                raise ValueError(f"Invalid priority: {action.value}")
            ticket.current_priority = value
            if value == expectation.priority and metadata.get("first_correct_priority_step") is None:
                metadata["first_correct_priority_step"] = self._state.step_count
            ticket.metadata = metadata
            self._last_result = f"Set {ticket.ticket_id} priority to {value}."
            return

        if action.operation == "assign_team":
            value = (action.value or "").lower()
            if value not in VALID_TEAMS:
                raise ValueError(f"Invalid team: {action.value}")
            ticket.current_team = value
            if value == expectation.team and metadata.get("first_correct_team_step") is None:
                metadata["first_correct_team_step"] = self._state.step_count
            ticket.metadata = metadata
            self._last_result = f"Assigned {ticket.ticket_id} to {value}."
            return

        if action.operation == "add_tag":
            if not action.value:
                raise ValueError("Tag value is required.")
            tag = action.value.strip().lower()
            if tag not in ticket.tags:
                ticket.tags.append(tag)
            ticket.metadata = metadata
            self._last_result = f"Added tag '{tag}' to {ticket.ticket_id}."
            return

        if action.operation == "send_reply":
            if not action.message:
                raise ValueError("message is required for send_reply.")
            ticket.last_reply = action.message.strip()
            ticket.metadata = metadata
            self._last_result = f"Sent a customer reply on {ticket.ticket_id}."
            return

        if action.operation == "resolve_ticket":
            if not action.value:
                raise ValueError("Resolution code is required.")
            metadata["resolution_code"] = action.value.strip().lower()
            if expectation.status == "open" or (
                expectation.must_inspect and not metadata.get("inspected")
            ):
                metadata["safety_breach"] = True
            ticket.metadata = metadata
            ticket.current_status = "resolved"
            self._last_result = (
                f"Resolved {ticket.ticket_id} with code {metadata['resolution_code']}."
            )
            return

        raise ValueError(f"Unsupported operation: {action.operation}")

    def _grade(self) -> GraderBreakdown:
        assert self._task is not None
        return grade_task(self._task, self._tickets)

    def _update_dynamics(self) -> None:
        if self._task is None:
            return

        for ticket_id, expectation in self._task.expectations.items():
            ticket = self._tickets[ticket_id]
            metadata = deepcopy(ticket.metadata or {})

            if (
                expectation.priority_due_step is not None
                and self._state.step_count > expectation.priority_due_step
                and ticket.current_priority != expectation.priority
            ):
                metadata["sla_breach"] = True

            if (
                expectation.team_due_step is not None
                and self._state.step_count > expectation.team_due_step
                and ticket.current_team != expectation.team
            ):
                metadata["sla_breach"] = True

            ticket.metadata = metadata

    def _observation(
        self,
        *,
        done: bool,
        reward: float,
        breakdown: GraderBreakdown,
    ) -> SupportTriageObservation:
        assert self._task is not None
        task_card = TaskCard(
            task_id=self._task.task_id,
            name=self._task.name,
            difficulty=self._task.difficulty,
            objective=self._task.objective,
            completion_hint=self._task.completion_hint,
        )
        remaining_steps = max(self._max_steps - self._state.step_count, 0)
        return SupportTriageObservation(
            task=task_card,
            tickets=list(self._tickets.values()),
            allowed_operations=[
                "inspect_ticket",
                "set_priority",
                "assign_team",
                "add_tag",
                "send_reply",
                "resolve_ticket",
                "submit",
            ],
            last_result=self._last_result,
            remaining_steps=remaining_steps,
            current_score=breakdown.overall_score,
            grader_breakdown=GraderBreakdown(
                overall_score=breakdown.overall_score,
                ticket_scores=breakdown.ticket_scores,
                notes=[],
            ),
            done=done,
            reward=reward,
            metadata={
                "episode_id": self._state.episode_id,
                "step_count": self._state.step_count,
            },
        )
