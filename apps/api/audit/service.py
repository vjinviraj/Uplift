import json

from sqlmodel import Session

from apps.api.models import AuditEvent


def record_audit_event(
    *,
    session: Session,
    agent_run_id: str,
    session_id: str,
    actor_type: str,
    action_id: str,
    event_type: str,
    decision: str | None = None,
    reason: str | None = None,
    policy_version: str | None = None,
    razorpay_order_id: str | None = None,
    razorpay_payment_id: str | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        agent_run_id=agent_run_id,
        session_id=session_id,
        actor_type=actor_type,
        action_id=action_id,
        event_type=event_type,
        decision=decision,
        reason=reason,
        policy_version=policy_version,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        payload_json=json.dumps(payload or {}),
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event