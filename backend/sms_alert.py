"""
STUB that logs alerts to sms_log.csv
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import storagecsv as storage

DEMO_IEBC_NUMBER = os.getenv("DEMO_IEBC_NUMBER", "+25470000000")

def send_iebc_sms(alert_payload: dict) -> dict:
    #STUB-send an SMS to IEBC with an evidence pointer

    to = alert_payload.get("to") or DEMO_IEBC_NUMBER
    tx_id = alert_payload.get("transaction_id", "")
    candidate_id = alert_payload.get("candidate_id", "")
    reasons = alert_payload.get("reasons", [])

    #Short SMS string
    deadline = alert_payload.get("escalation_deadline", "")
    msg = (
        f"CivicLens ALERT: Transaction {tx_id} candidate {candidate_id} reasons {','.join(reasons)[:60]}"
        + (f"deadline {deadline}" if deadline else "")
    )

    #STUB": Write to sms_log.csv as proof
    log_row = storage._append_sms_log({
        "to": to,
        "transaction_id": tx_id,
        "candidate_id": candidate_id,
        "reasons": ";".join(reasons) if isinstance(reasons, list) else str(reasons),
        "payload": json.dumps({"message": msg, **alert_payload}, ensure_ascii=False),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })

    #Also print for dev console
    print(f"[SMS-STUB] to={to} message={msg}")
    return log_row