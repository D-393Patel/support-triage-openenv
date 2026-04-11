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
    must_inspect: bool = False
    priority_due_step: Optional[int] = None
    team_due_step: Optional[int] = None


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


def ticket(
    ticket_id: str,
    customer_tier: str,
    channel: str,
    subject: str,
    summary: str,
    hidden_context: List[str],
    sla_minutes_remaining: Optional[int],
) -> TicketSeed:
    return TicketSeed(
        ticket_id=ticket_id,
        customer_tier=customer_tier,
        channel=channel,
        subject=subject,
        summary=summary,
        hidden_context=hidden_context,
        sla_minutes_remaining=sla_minutes_remaining,
    )


def expect(
    *,
    priority: Optional[str] = None,
    team: Optional[str] = None,
    required_tags: Optional[List[str]] = None,
    reply_keywords: Optional[List[str]] = None,
    status: Optional[str] = None,
    resolution_code: Optional[str] = None,
    must_inspect: bool = False,
    priority_due_step: Optional[int] = None,
    team_due_step: Optional[int] = None,
) -> TicketExpectation:
    return TicketExpectation(
        priority=priority,
        team=team,
        required_tags=required_tags or [],
        reply_keywords=reply_keywords or [],
        status=status,
        resolution_code=resolution_code,
        must_inspect=must_inspect,
        priority_due_step=priority_due_step,
        team_due_step=team_due_step,
    )


TASKS: List[TaskSpec] = [
    TaskSpec(
        task_id="billing_refund_easy",
        name="Duplicate charge refund",
        difficulty="easy",
        objective=(
            "Handle a billing dispute where the visible complaint sounds routine but the internal "
            "ledger determines whether immediate refund approval is safe."
        ),
        completion_hint=(
            "Inspect first, confirm finance policy, communicate the refund timeline clearly, and only "
            "then close the ticket."
        ),
        max_steps=9,
        tickets=[
            ticket(
                ticket_id="T-100",
                customer_tier="pro",
                channel="email",
                subject="Charged twice for March subscription",
                summary=(
                    "Customer reports seeing two March subscription charges and wants the extra "
                    "payment reversed."
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
            "T-100": expect(
                priority="high",
                team="billing",
                required_tags=["refund", "duplicate-charge"],
                reply_keywords=["refund", "3-5", "apolog"],
                status="resolved",
                resolution_code="refund_approved",
                must_inspect=True,
            )
        },
    ),
    TaskSpec(
        task_id="invoice_copy_easy",
        name="VAT invoice copy",
        difficulty="easy",
        objective=(
            "Resolve a routine billing document request, but only after verifying the internal note "
            "that the compliant invoice is already available."
        ),
        completion_hint=(
            "Inspect the billing context, route to billing, mention invoice availability, and resolve "
            "once delivery is confirmed."
        ),
        max_steps=8,
        tickets=[
            ticket(
                ticket_id="T-110",
                customer_tier="starter",
                channel="email",
                subject="Need VAT invoice for travel reimbursement",
                summary=(
                    "Customer needs a VAT invoice copy for reimbursement and says their billing "
                    "details were already sent last week."
                ),
                hidden_context=[
                    "The compliant VAT invoice is already generated in the billing system.",
                    "Billing can send it immediately without further verification.",
                    "Safe to resolve once the invoice is confirmed sent.",
                ],
                sla_minutes_remaining=720,
            )
        ],
        expectations={
            "T-110": expect(
                priority="low",
                team="billing",
                required_tags=["invoice"],
                reply_keywords=["invoice"],
                status="resolved",
                resolution_code="invoice_sent",
                must_inspect=True,
            )
        },
    ),
    TaskSpec(
        task_id="feature_feedback_easy",
        name="Feature feedback acknowledgment",
        difficulty="easy",
        objective=(
            "Acknowledge a product request, verify the internal routing note, and close it only after "
            "confirming the feedback was forwarded appropriately."
        ),
        completion_hint=(
            "Inspect the product context, route to product, tag it as a feature request, reply that it "
            "was forwarded, and resolve."
        ),
        max_steps=8,
        tickets=[
            ticket(
                ticket_id="T-120",
                customer_tier="starter",
                channel="portal",
                subject="Please add dark mode to analytics dashboards",
                summary=(
                    "Customer wants dark mode for analytics and asks whether the idea has actually "
                    "been captured by the product team."
                ),
                hidden_context=[
                    "Product team owns feature requests for dashboard UX.",
                    "Safe to resolve once the feedback is acknowledged as forwarded.",
                    "No engineering escalation is required at this stage.",
                ],
                sla_minutes_remaining=2880,
            )
        ],
        expectations={
            "T-120": expect(
                priority="low",
                team="product",
                required_tags=["feature-request"],
                reply_keywords=["forward"],
                status="resolved",
                resolution_code="forwarded_to_product",
                must_inspect=True,
            )
        },
    ),
    TaskSpec(
        task_id="account_security_medium",
        name="Account security triage",
        difficulty="medium",
        objective=(
            "Triage two simultaneous tickets where one is a likely compromise and the other is a "
            "routine invoice request. Use inspection to avoid resolving the wrong case."
        ),
        completion_hint=(
            "The risky login ticket stays open with verification guidance; the invoice ticket goes to "
            "billing and can be resolved."
        ),
        max_steps=16,
        tickets=[
            ticket(
                ticket_id="T-200",
                customer_tier="enterprise",
                channel="chat",
                subject="Password changed and MFA phone no longer works",
                summary=(
                    "Workspace admin reports the password changed unexpectedly and the MFA phone was "
                    "replaced overnight."
                ),
                hidden_context=[
                    "Security playbook says do not resolve until identity verification completes.",
                    "High-value workspace with active suspicious IP alerts.",
                    "Response should ask the customer to verify identity and mention account security.",
                ],
                sla_minutes_remaining=30,
            ),
            ticket(
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
            "T-200": expect(
                priority="urgent",
                team="security",
                required_tags=["account-takeover", "verification"],
                reply_keywords=["verify", "security", "account"],
                status="open",
                must_inspect=True,
                priority_due_step=3,
                team_due_step=5,
            ),
            "T-201": expect(
                priority="low",
                team="billing",
                required_tags=["invoice"],
                reply_keywords=["invoice"],
                status="resolved",
                resolution_code="invoice_sent",
                must_inspect=True,
            ),
        },
    ),
    TaskSpec(
        task_id="privacy_billing_medium",
        name="Privacy and billing split queue",
        difficulty="medium",
        objective=(
            "Handle a GDPR deletion request alongside a duplicate-charge refund. Inspection is "
            "required to keep the privacy case open while safely closing the billing case."
        ),
        completion_hint=(
            "Compliance owns the deletion request and it stays open pending verification; the refund "
            "case belongs to billing and can be completed."
        ),
        max_steps=16,
        tickets=[
            ticket(
                ticket_id="T-210",
                customer_tier="pro",
                channel="email",
                subject="Delete all personal data under GDPR",
                summary=(
                    "Customer requests full account data deletion and asks what verification is "
                    "required before processing."
                ),
                hidden_context=[
                    "Compliance owns deletion workflows.",
                    "Reply should mention identity verification and the 30-day fulfillment window.",
                    "Do not resolve before verification completes.",
                ],
                sla_minutes_remaining=1440,
            ),
            ticket(
                ticket_id="T-211",
                customer_tier="pro",
                channel="email",
                subject="I was billed twice for annual add-on seats",
                summary=(
                    "Customer sees a duplicate seat expansion charge and wants the accidental payment "
                    "reversed."
                ),
                hidden_context=[
                    "Duplicate add-on charge is confirmed in the ledger.",
                    "Finance policy allows immediate refund approval for accidental duplicate charges.",
                    "Reply should mention the 3-5 business day refund window.",
                ],
                sla_minutes_remaining=360,
            ),
        ],
        expectations={
            "T-210": expect(
                priority="high",
                team="compliance",
                required_tags=["gdpr", "data-deletion"],
                reply_keywords=["verify", "30", "delete"],
                status="open",
                must_inspect=True,
                team_due_step=6,
            ),
            "T-211": expect(
                priority="high",
                team="billing",
                required_tags=["refund", "duplicate-charge"],
                reply_keywords=["refund", "3-5"],
                status="resolved",
                resolution_code="refund_approved",
                must_inspect=True,
            ),
        },
    ),
    TaskSpec(
        task_id="sla_multiqueue_hard",
        name="Enterprise SLA multiqueue",
        difficulty="hard",
        objective=(
            "Balance an enterprise outage, a GDPR deletion request, and a product feature request. "
            "Inspection should change how quickly and safely you act on each queue."
        ),
        completion_hint=(
            "Escalate the outage urgently, route the privacy case to compliance without resolving it, "
            "and only close the feature request after forwarding it."
        ),
        max_steps=24,
        tickets=[
            ticket(
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
            ticket(
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
            ticket(
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
            "T-300": expect(
                priority="urgent",
                team="engineering",
                required_tags=["outage", "vip", "sla-risk"],
                reply_keywords=["incident", "update", "engineering"],
                status="open",
                must_inspect=True,
                priority_due_step=4,
                team_due_step=6,
            ),
            "T-301": expect(
                priority="high",
                team="compliance",
                required_tags=["gdpr", "data-deletion"],
                reply_keywords=["verify", "30", "delete"],
                status="open",
                must_inspect=True,
            ),
            "T-302": expect(
                priority="low",
                team="product",
                required_tags=["feature-request"],
                reply_keywords=["forward"],
                status="resolved",
                resolution_code="forwarded_to_product",
                must_inspect=True,
            ),
        },
    ),
    TaskSpec(
        task_id="security_compliance_hard",
        name="Security, privacy, and revenue risk",
        difficulty="hard",
        objective=(
            "Balance a suspected OAuth compromise, a GDPR deletion request, and an urgent refund "
            "case. Two tickets must remain open while the billing case can be safely completed."
        ),
        completion_hint=(
            "Security and compliance cases stay open after the right escalation and reply. Only the "
            "duplicate-charge refund should be closed."
        ),
        max_steps=24,
        tickets=[
            ticket(
                ticket_id="T-320",
                customer_tier="enterprise",
                channel="chat",
                subject="Unknown OAuth app approved itself in our workspace",
                summary=(
                    "Workspace owner sees a previously unseen OAuth integration with suspicious "
                    "permissions and believes the workspace may be compromised."
                ),
                hidden_context=[
                    "Security team owns suspicious OAuth and account-takeover investigations.",
                    "Do not resolve until identity and workspace control are verified.",
                    "Reply should ask for verification and mention account security review.",
                ],
                sla_minutes_remaining=45,
            ),
            ticket(
                ticket_id="T-321",
                customer_tier="pro",
                channel="email",
                subject="Please erase all stored personal data",
                summary=(
                    "Customer wants their personal data removed and asks what happens next before "
                    "the request can be processed."
                ),
                hidden_context=[
                    "Compliance owns deletion workflows.",
                    "Reply should mention identity verification and the 30-day completion window.",
                    "Do not resolve before verification completes.",
                ],
                sla_minutes_remaining=1440,
            ),
            ticket(
                ticket_id="T-322",
                customer_tier="pro",
                channel="email",
                subject="Annual plan charged twice after seat upgrade",
                summary=(
                    "Customer reports a second annual charge after a recent seat expansion and wants "
                    "the accidental duplicate payment reversed."
                ),
                hidden_context=[
                    "Duplicate annual charge is confirmed in the billing ledger.",
                    "Finance policy allows immediate refund approval for confirmed duplicate charges.",
                    "Reply should mention the refund timeline of 3-5 business days.",
                ],
                sla_minutes_remaining=300,
            ),
        ],
        expectations={
            "T-320": expect(
                priority="urgent",
                team="security",
                required_tags=["account-takeover", "verification"],
                reply_keywords=["verify", "security", "workspace"],
                status="open",
                must_inspect=True,
                priority_due_step=4,
                team_due_step=6,
            ),
            "T-321": expect(
                priority="high",
                team="compliance",
                required_tags=["gdpr", "data-deletion"],
                reply_keywords=["verify", "30", "delete"],
                status="open",
                must_inspect=True,
            ),
            "T-322": expect(
                priority="high",
                team="billing",
                required_tags=["refund", "duplicate-charge"],
                reply_keywords=["refund", "3-5", "apolog"],
                status="resolved",
                resolution_code="refund_approved",
                must_inspect=True,
            ),
        },
    ),
]

TASK_LOOKUP: Dict[str, TaskSpec] = {task.task_id: task for task in TASKS}
