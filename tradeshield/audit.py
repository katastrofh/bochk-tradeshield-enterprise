from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from tradeshield.models import AuditEvent, User


GENESIS_HASH = "0" * 64


def _canonical_hash(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def record_event(
    db: Session,
    *,
    actor: User | None,
    event_type: str,
    event_summary: str,
    case_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    last = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
    previous_hash = last.event_hash if last else GENESIS_HASH
    actor_email = actor.email if actor else "system@tradeshield.ai"
    actor_role = actor.role if actor else "SYSTEM"
    now = datetime.utcnow()
    body = {
        "case_id": case_id,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "event_type": event_type,
        "event_summary": event_summary,
        "payload": payload or {},
        "previous_hash": previous_hash,
        "created_at": now.isoformat(),
    }
    event_hash = _canonical_hash(body)
    ev = AuditEvent(
        case_id=case_id,
        actor_email=actor_email,
        actor_role=actor_role,
        event_type=event_type,
        event_summary=event_summary,
        payload=payload or {},
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=now,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def verify_audit_chain(db: Session) -> dict[str, Any]:
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    prev = GENESIS_HASH
    for ev in events:
        if ev.previous_hash != prev:
            return {"valid": False, "failed_event_id": ev.id, "reason": "previous_hash mismatch"}
        body = {
            "case_id": ev.case_id,
            "actor_email": ev.actor_email,
            "actor_role": ev.actor_role,
            "event_type": ev.event_type,
            "event_summary": ev.event_summary,
            "payload": ev.payload,
            "previous_hash": ev.previous_hash,
            "created_at": ev.created_at.isoformat(),
        }
        expected = _canonical_hash(body)
        if expected != ev.event_hash:
            return {"valid": False, "failed_event_id": ev.id, "reason": "event_hash mismatch"}
        prev = ev.event_hash
    return {"valid": True, "events_checked": len(events), "latest_hash": prev}
