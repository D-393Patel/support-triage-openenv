"""Built-in tasks and deterministic grader targets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TicketSeed:
    ticket_id: str
    customer_tier: str
    subject: str
    channel: str
    summary: str
    hidden_context: List[str]
    sla_minutes_remaining: Optional[int] = None


@dataclass(frozen=True)
class TicketExpectation:
    priority: Optional[str] = None
    team: Optional[str] = None
    required_tags: List[str] = field(default_factory=list)
    reply_keywords: List[str] = field(default_factory=list)
    status: Optional[str] = None
    resolution_code: Optional[str] = None


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    name: str
    difficulty: str
    objective: str
    completion_hint: str
    max_steps: int
    tickets: List[TicketSeed]
    expectations: Dict[str, TicketExpectation]


TASKS: List[TaskSpec] = [
    TaskSpec(
        task_id="billing_refund_easy",
        name="Duplicate charge refund",
        difficulty="easy",
        objective=(
            "Handle a single billing ticket. Inspect the ticket, triage it correctly, "
            "reply with the right customer-facing guidance, and close it when safe."
        ),
        completion_hint=(
            "A perfect run sets the right billing priority, tags the refund correctly, "
            "confirms the refund timeline, and resolves the ticket."
        ),
        max_steps=8,
        tickets=[
            TicketSeed(
                ticket_id="T-100",
                customer_tier="pro",
                channel="email",
                subject="Charged twice for March subscription",
                summary=(
                    "Customer reports seeing the same subscription charge twice on the same day "
                    "and wants the extra payment reversed."
                ),
                hidden_context=[
                    "Duplicate payment is confirmed in the billing ledger.",
                    "Finance policy allows immediate refund approval for duplicate charges.",
                    "Standard promise window is 3-5 business days.",
                ],
                sla_minutes_remaining=240,
            )
        ],
        expectations={
            "T-100": TicketExpectation(
                priority="high",
                team="billing",
                required_tags=["refund", "duplicate-charge"],
                reply_keywords=["refund", "3-5", "apolog"],
                status="resolved",
                resolution_code="refund_approved",
            )
        },
    ),
    TaskSpec(
        task_id="account_security_medium",
        name="Account security triage",
        difficulty="medium",
        objective=(
            "Triage two simultaneous tickets. One is an account-takeover risk that needs rapid "
            "security handling, while the other is a routine billing request."
        ),
        completion_hint=(
            "The risky login ticket should stay open with a verification-oriented reply; the invoice "
            "ticket should be routed to billing and safely resolved."
        ),
        max_steps=14,
        tickets=[
            TicketSeed(
                ticket_id="T-200",
                customer_tier="enterprise",
                channel="chat",
                subject="Password changed and MFA phone no longer works",
                summary=(
                    "Admin says the account password changed unexpectedly and the MFA phone was "
                    "replaced. They suspect compromise."
                ),
                hidden_context=[
                    "Security playbook says do not resolve until identity verification completes.",
                    "High-value workspace with active suspicious IP alerts.",
                    "Response should ask the customer to verify identity and mention account security.",
                ],
                sla_minutes_remaining=30,
            ),
            TicketSeed(
                ticket_id="T-201",
                customer_tier="starter",
                channel="email",
                subject="Need VAT invoice for last month",
                summary=(
                    "Customer needs a compliant VAT invoice copy for reimbursement and already provided "
                    "their billing details."
                ),
                hidden_context=[
                    "Billing can fulfill this directly.",
                    "Once invoice delivery is confirmed, the ticket may be resolved.",
                    "Reply should mention invoice availability.",
                ],
                sla_minutes_remaining=720,
            ),
        ],
        expectations={
            "T-200": TicketExpectation(
                priority="urgent",
                team="security",
                required_tags=["account-takeover", "verification"],
                reply_keywords=["verify", "security", "account"],
                status="open",
            ),
            "T-201": TicketExpectation(
                priority="low",
                team="billing",
                required_tags=["invoice"],
                reply_keywords=["invoice"],
                status="resolved",
                resolution_code="invoice_sent",
            ),
        },
    ),
    TaskSpec(
        task_id="sla_multiqueue_hard",
        name="Enterprise SLA multiqueue",
        difficulty="hard",
        objective=(
            "Balance an enterprise outage, a GDPR deletion request, and a product feature request. "
            "Use inspection context to route each ticket, protect SLA-sensitive work, and only close "
            "what is safe to close."
        ),
        completion_hint=(
            "The outage needs urgent engineering escalation, the GDPR request belongs with compliance, "
            "and the feature request can be tagged and resolved as forwarded."
        ),
        max_steps=18,
        tickets=[
            TicketSeed(
                ticket_id="T-300",
                customer_tier="enterprise",
                channel="chat",
                subject="EU region API is timing out for all production traffic",
                summary=(
                    "Customer says every API request in EU production is timing out and revenue events "
                    "are dropping."
                ),
                hidden_context=[
                    "SLA breach risk in under 20 minutes.",
                    "Incident process requires urgent engineering ownership and proactive updates.",
                    "Keep ticket open until incident is mitigated.",
                ],
                sla_minutes_remaining=18,
            ),
            TicketSeed(
                ticket_id="T-301",
                customer_tier="pro",
                channel="email",
                subject="Delete all personal data under GDPR",
                summary=(
                    "Customer requests full account data deletion and asks what verification is needed."
                ),
                hidden_context=[
                    "Compliance owns deletion workflows.",
                    "Reply should mention identity verification and the 30-day fulfillment window.",
                    "Do not resolve before verification completes.",
                ],
                sla_minutes_remaining=1440,
            ),
            TicketSeed(
                ticket_id="T-302",
                customer_tier="starter",
                channel="portal",
                subject="Please add dark mode to analytics dashboards",
                summary=(
                    "Customer requests dark mode in the analytics dashboards and wants to know whether "
                    "the idea has been captured."
                ),
                hidden_context=[
                    "Product team owns feature requests.",
                    "It is safe to resolve after acknowledging the feedback was forwarded.",
                ],
                sla_minutes_remaining=4320,
            ),
        ],
        expectations={
            "T-300": TicketExpectation(
                priority="urgent",
                team="engineering",
                required_tags=["outage", "vip", "sla-risk"],
                reply_keywords=["incident", "update", "engineering"],
                status="open",
            ),
            "T-301": TicketExpectation(
                priority="high",
                team="compliance",
                required_tags=["gdpr", "data-deletion"],
                reply_keywords=["verify", "30", "delete"],
                status="open",
            ),
            "T-302": TicketExpectation(
                priority="low",
                team="product",
                required_tags=["feature-request"],
                reply_keywords=["forward"],
                status="resolved",
                resolution_code="forwarded_to_product",
            ),
        },
    ),
]

TASK_LOOKUP: Dict[str, TaskSpec] = {task.task_id: task for task in TASKS}
