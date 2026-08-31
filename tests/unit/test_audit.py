import json

from sqlmodel import Session

from apps.api.audit.service import record_audit_event
from apps.api.database import engine
from apps.api.models import AuditEvent


def test_record_audit_event_persists_event():
    with Session(engine) as session:
        event = record_audit_event(
            session=session,
            agent_run_id="run-001",
            session_id="session-001",
            actor_type="merchant_agent",
            action_id="action-001",
            event_type="policy_checked",
            decision="ALLOWED",
            reason="Order is within policy limits.",
            policy_version="v1",
            payload={"total_paise": 300_000},
        )

        assert event.id is not None
        assert event.event_type == "policy_checked"
        assert event.decision == "ALLOWED"
        assert event.policy_version == "v1"

        stored = session.get(type(event), event.id)

        assert stored is not None
        assert stored.reason == "Order is within policy limits."

def test_audit_events_are_append_only():
    with Session(engine) as session:
        first = record_audit_event(
            session=session,
            agent_run_id="run-002",
            session_id="session-002",
            actor_type="merchant_agent",
            action_id="action-001",
            event_type="policy_checked",
            decision="ALLOWED",
            reason="First decision.",
            policy_version="v1",
            payload={"total_paise": 300_000},
        )

        second = record_audit_event(
            session=session,
            agent_run_id="run-002",
            session_id="session-002",
            actor_type="merchant_agent",
            action_id="action-002",
            event_type="upsell_proposed",
            decision="ALLOWED",
            reason="Second event.",
            policy_version="v1",
            payload={"upsell_product_id": "ACC-001"},
        )

        assert first.id != second.id

        stored_first = session.get(AuditEvent, first.id)
        stored_second = session.get(AuditEvent, second.id)

        assert stored_first is not None
        assert stored_second is not None

        assert stored_first.event_type == "policy_checked"
        assert stored_first.reason == "First decision."

        assert stored_second.event_type == "upsell_proposed"
        assert stored_second.reason == "Second event."

def test_audit_payload_is_serialized_as_json():
    with Session(engine) as session:
        event = record_audit_event(
            session=session,
            agent_run_id="run-003",
            session_id="session-003",
            actor_type="policy_engine",
            action_id="action-001",
            event_type="policy_checked",
            decision="ALLOWED",
            reason="Policy passed.",
            policy_version="v1",
            payload={
                "total_paise": 300_000,
                "buyer_budget_paise": 500_000,
                "upsell_count": 1,
            },
        )

        stored_payload = json.loads(event.payload_json)

        assert stored_payload == {
            "total_paise": 300_000,
            "buyer_budget_paise": 500_000,
            "upsell_count": 1,
        }

