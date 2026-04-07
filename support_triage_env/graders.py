"""Deterministic task graders and reward helpers."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from support_triage_env.models import GraderBreakdown, TicketView
from support_triage_env.tasks import TaskSpec

EPSILON = 0.001


def _strict_score(value: float) -> float:
    bounded = max(0.0, min(1.0, value))
    return EPSILON + (1.0 - (2.0 * EPSILON)) * bounded


def _contains_keywords(text: str | None, keywords: Iterable[str]) -> float:
    expected = [keyword.lower() for keyword in keywords]
    if not expected:
        return _strict_score(1.0)
    haystack = (text or "").lower()
    matches = sum(1 for keyword in expected if keyword in haystack)
    return _strict_score(matches / len(expected))


def _tag_score(actual_tags: Iterable[str], expected_tags: Iterable[str]) -> float:
    expected = {tag.lower() for tag in expected_tags}
    if not expected:
        return _strict_score(1.0)
    actual = {tag.lower() for tag in actual_tags}
    return _strict_score(len(actual & expected) / len(expected))


def score_ticket(ticket: TicketView, expectation) -> Tuple[float, list[str]]:
    notes: list[str] = []
    checks = []

    if expectation.priority:
        priority_score = _strict_score(
            1.0 if ticket.current_priority == expectation.priority else 0.0
        )
        checks.append(priority_score)
        if priority_score <= _strict_score(0.0):
            notes.append(f"{ticket.ticket_id}: priority should be {expectation.priority}.")

    if expectation.team:
        team_score = _strict_score(1.0 if ticket.current_team == expectation.team else 0.0)
        checks.append(team_score)
        if team_score <= _strict_score(0.0):
            notes.append(f"{ticket.ticket_id}: team should be {expectation.team}.")

    if expectation.required_tags:
        tags_score = _tag_score(ticket.tags, expectation.required_tags)
        checks.append(tags_score)
        if tags_score < 1.0:
            notes.append(f"{ticket.ticket_id}: missing one or more required tags.")

    if expectation.reply_keywords:
        reply_score = _contains_keywords(ticket.last_reply, expectation.reply_keywords)
        checks.append(reply_score)
        if reply_score < 1.0:
            notes.append(f"{ticket.ticket_id}: reply is missing required guidance.")

    if expectation.status:
        status_score = _strict_score(1.0 if ticket.current_status == expectation.status else 0.0)
        checks.append(status_score)
        if status_score <= _strict_score(0.0):
            notes.append(f"{ticket.ticket_id}: status should be {expectation.status}.")

    if expectation.resolution_code:
        resolution_score = _strict_score(
            1.0
            if (ticket.metadata or {}).get("resolution_code") == expectation.resolution_code
            else 0.0
        )
        checks.append(resolution_score)
        if resolution_score <= _strict_score(0.0):
            notes.append(f"{ticket.ticket_id}: resolution should be {expectation.resolution_code}.")

    if not checks:
        return _strict_score(1.0), notes
    return _strict_score(sum(checks) / len(checks)), notes


def grade_task(task: TaskSpec, tickets: Dict[str, TicketView]) -> GraderBreakdown:
    ticket_scores: Dict[str, float] = {}
    notes: list[str] = []

    for ticket_id, expectation in task.expectations.items():
        ticket = tickets[ticket_id]
        ticket_score, ticket_notes = score_ticket(ticket, expectation)
        ticket_scores[ticket_id] = round(ticket_score, 4)
        notes.extend(ticket_notes)

    overall = _strict_score(sum(ticket_scores.values()) / max(len(ticket_scores), 1))
    return GraderBreakdown(
        overall_score=round(overall, 4),
        ticket_scores=ticket_scores,
        notes=notes,
    )
