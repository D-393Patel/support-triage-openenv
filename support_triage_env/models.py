"""Typed models for the support triage environment."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

try:
    from openenv.core.env_server.types import Action, Observation
except ImportError:
    from openenv.core.env_server.types import Action, Observation


Priority = Literal["low", "medium", "high", "urgent"]
Team = Literal["billing", "security", "engineering", "compliance", "product", "general"]
Status = Literal["open", "waiting_on_customer", "resolved"]
Operation = Literal[
    "inspect_ticket",
    "set_priority",
    "assign_team",
    "add_tag",
    "send_reply",
    "resolve_ticket",
    "submit",
]


class TicketView(BaseModel):
    ticket_id: str
    customer_tier: str
    subject: str
    channel: str
    summary: str
    current_priority: Optional[Priority] = None
    current_team: Optional[Team] = None
    current_status: Status = "open"
    tags: List[str] = Field(default_factory=list)
    last_reply: Optional[str] = None
    visible_context: List[str] = Field(default_factory=list)
    sla_minutes_remaining: Optional[int] = None
    metadata: Dict[str, object] = Field(default_factory=dict, exclude=True)


class TaskCard(BaseModel):
    task_id: str
    name: str
    difficulty: Literal["easy", "medium", "hard"]
    objective: str
    completion_hint: str


class GraderBreakdown(BaseModel):
    overall_score: float
    ticket_scores: Dict[str, float] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class SupportTriageAction(Action):
    operation: Operation = Field(..., description="Action to execute in the support queue")
    ticket_id: Optional[str] = Field(None, description="Target ticket identifier")
    value: Optional[str] = Field(None, description="Priority, team, tag, or resolution code")
    message: Optional[str] = Field(None, description="Agent reply to the customer")


class SupportTriageObservation(Observation):
    task: TaskCard
    tickets: List[TicketView]
    allowed_operations: List[Operation]
    last_result: str
    remaining_steps: int
    current_score: float = Field(..., ge=0.0, le=1.0)
    grader_breakdown: GraderBreakdown
