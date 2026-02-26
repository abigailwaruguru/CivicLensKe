#Rule engine: Defining Rules based on 
#Kenya Election Campaign Financing Act
import pandas as pd
from datetime import datetime, timedelta

#Constants
#Max amount per donation otherwise CAP_BREACH
CAP_KES = 100_000
#Donations from the same donor within window triggers FREQ_HIGH
SUSPICIOUS_FREQ_COUNT = 5
#Time window for frequecy check in hours
SUSPICIOUS_FREQ_WINDOW = 2
#Window for counting locks
LOCK_WINDOW_DAYS = 30
#Locks within window before BAN
BAN_AFTER_LOCKS = 2
#Auto-generate receipt above this amount
RECEIPT_THRESHOLD_KES = 50_000
#Window for multi-candiate donor check
MULTI_CANDIDATE_WINDOW_HOURS = 48

#Receives new transaction and Checks along all past Transactions
def run_rules(transaction: dict, all_transactions: pd.DataFrame) -> dict:
    """
    Run all rule checks against a transaction
    Returns: reasons: [str], status: str, explain: str
    """
    reasons =[]
    explanations = []

    amount = float(transaction.get("amount_kes", 0))
    donor_id = transaction.get("donor_id", "")
    candiadate_id  = transaction.get("candidate_id", "")
    ts = transaction.get("timestamp", datetime.utcnow().isoformat())


    #Convert to date time format
    try:
        tx_time = datetime.fromisoformat(ts)
    except Exception:
        tx_time = datetime.utcnow()

    #Rule checks declarations
    #1. CAP BREACH
    if amount> CAP_KES:
        reasons.append("CAP_BREACH")
        explanations.append(
            f"Donation of KES {amount:,.0f} exceeds the contribution cap of {CAP_KES:,.0f}."
        )
    
    #2. ANONYMOUS_DONATION
    if transaction.get("is_anonymous", False):
        reasons.append("ANONYMOUS_DONATION")
        explanations.append("Donor is unknown. Anonymous donations are prohibited")

    #3. ILLEGAL_SOURCE
    if transaction.get("is_illegal_source",False):
        reasons.append("ILLEGAL_SOURCE")
        explanations.append("Contribution is from an illegal source")

    #4. PUBLIC_RESOURCE
    if transaction.get("is_public_resource",False):
        reasons.append("PUBLIC_RESOURCE")
        explanations.append("Suspected use of public resources")

    #5. FREQ_HIGH - contributions by same donor to same candidate within window
    if donor_id and not all_transactions.empty:
        window_start = tx_time - timedelta(hours = SUSPICIOUS_FREQ_WINDOW)
        recent = all_transactions[
            (all_transactions["donor_id"] == donor_id) &
            (all_transactions["candidate_id"] == candiadate_id) &
            (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
        ]

        if len (recent) >= SUSPICIOUS_FREQ_COUNT:
            reasons.append("FREQ_HIGH")
            explanations.append(
                f"Donor has made {len(recent)} donations to this candidate in the last"
                f"{SUSPICIOUS_FREQ_WINDOW} hours (threshold: {SUSPICIOUS_FREQ_COUNT})."
            )
    
    #6. MULTI_CANDIDATE_DONOR - contributions by same donor to different candidates within window
    if donor_id and not all_transactions.empty:
        window_start = tx_time - timedelta(hours = MULTI_CANDIDATE_WINDOW_HOURS)
        recent_candidates = all_transactions[
            (all_transactions["donor_id"] == donor_id) &
            (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start) &
            (all_transactions["candidate_id"] == candiadate_id)
        ]["candidate_id"].unique()
        
        if len(recent_candidates) >= 2:
            reasons.append("MULTI_CANDIDATE_DONOR")
            explanations.append(
                f"Donor has contributed to {len(recent_candidates)}"
                f"within{MULTI_CANDIDATE_WINDOW_HOURS} hours."
            )

    #7. DISCLOSURE_REQUIRED
    if amount >= RECEIPT_THRESHOLD_KES:
        reasons.append("DISCLOSURE_REQUIRED")
        explanations.append(
            f"Donation of KES {amount: ,.0f} exceeds the disclosure threshold of {RECEIPT_THRESHOLD_KES: ,.0f}. Receipt required"
        )

    #Status - violation, suspicious, compliant
    violation_codes = {"CAP_BREACH", "ILLEGAL_SOURCE", "PUBLIC_RESOURCE", "ANONYMOUS_DONATION"}
    suspicious_codes = {"MULTI_CANDIDATE_DONOR", "FREQ_HIGH"}

    has_violations = any(r in violation_codes for r in reasons)
    has_suspicious = any(r in suspicious_codes for r in reasons)

    if has_violations:
        status = "Violation"
    elif has_suspicious:
        status = "Suspicious"
    else:
        status = "Compliant"
    
    explain = " ".join(explanations) if explanations else "Transaction meets all compliance requirements."

    return {
        "reasons": reasons,
        "status": status,
        "explain": explain
    }

#Define enforcemment actions
def compute_enforcements(candidate_id: str, new_status: str, all_transactions: pd.DataFrame) -> str:
    """
    Computes enforcement action based on candidates history
    Returns: NONE, ON_HOLD, LOCKED, BANNED
    """
    if new_status == "Suspicious":
        #Checks frequency of suspicious flags in the last 24Hrs
        window_start = datetime.utcnow() - timedelta(hours=SUSPICIOUS_FREQ_WINDOW)
        if not all_transactions.empty:
            recent_suspicious = all_transactions[
                (all_transactions["candidate_id"] == candidate_id) &
                (all_transactions["status"] == "Suspicious") &
                (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
                ]
            if len(recent_suspicious)>= SUSPICIOUS_FREQ_COUNT - 1:
                return "ON_HOLD"
            
    if new_status == "Violation":
        #Checks frequency of suspicious flags in the last 24Hrs
        lock_window_start = datetime.utcnow() - timedelta(days=LOCK_WINDOW_DAYS)
        if not all_transactions.empty:
            prior_locks = all_transactions[
                (all_transactions["candidate_id"] == candidate_id) &
                (all_transactions["enforcement_action"] == "LOCKED") &
                (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
                ]
            if len(prior_locks)>= BAN_AFTER_LOCKS - 1:
                return "BANNED"
        return "LOCKED"
    return "NONE"