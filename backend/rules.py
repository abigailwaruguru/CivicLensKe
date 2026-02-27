#Rule engine: Defining Rules based on 
#Kenya Election Campaign Financing Act
import pandas as pd
from datetime import datetime, timedelta, timezone

#Constants
#Max amount per donation otherwise CAP_BREACH
CAP_KES = 500_000
#Donations from the same donor within window triggers FREQ_HIGH
SUSPICIOUS_FREQ_COUNT = 3
#Time window for frequecy check in hours
SUSPICIOUS_FREQ_WINDOW = 12
#Window for counting locks
LOCK_WINDOW_DAYS = 30
#Locks within window before BAN
BAN_AFTER_LOCKS = 2
#Auto-generate receipt above this amount
RECEIPT_THRESHOLD_KES = 200_000
#Window for multi-candiate donor check
MULTI_CANDIDATE_WINDOW_HOURS = 24

#Define function to check new transaction against all past Transactions
def run_rules(transaction: dict, all_transactions: pd.DataFrame) -> dict:
    """
    Compares a new transaction against historical data to run compliance checks.
    Returns: dict with outcome reasons: [str], status: str, explain: [str]
    """
    #Initializes lists to store rule violations and explantaions
    reasons = []
    explanations = []

    #Get aspects of the new transaction that are to be cross checked
    #Defaults any missing to avoid errors
    amount = float(transaction.get("amount_kes", 0))
    donor_id = transaction.get("donor_id", "")
    candidate_id  = transaction.get("candidate_id", "")
    ts = transaction.get("timestamp", datetime.now(timezone.utc).isoformat())

    #Convert to date time format for python to do calculation of frequencies
    try:
        tx_time = datetime.fromisoformat(ts)
    except Exception:
        tx_time = datetime.now(timezone.utc)

    #Rule check declarations to determine return results (dict values)
    # ----- 1. CAP BREACH -----
    if amount> CAP_KES:
        reasons.append("CAP_BREACH")
        explanations.append(
            f"Donation of KES {amount:,.0f} exceeds the contribution cap of {CAP_KES:,.0f}."
        )
    
    # ----- 2. ANONYMOUS_DONATION -----
    if transaction.get("is_anonymous", False):
        reasons.append("ANONYMOUS_DONATION")
        explanations.append("Donor is unknown. Anonymous donations are prohibited")

    # ----- 3. ILLEGAL_SOURCE -----
    if transaction.get("is_illegal_source",False):
        reasons.append("ILLEGAL_SOURCE")
        explanations.append("Contribution is from an illegal source")

    # ----- 4. PUBLIC_RESOURCE -----
    if transaction.get("is_public_resource",False):
        reasons.append("PUBLIC_RESOURCE")
        explanations.append("Suspected use of public resources")

    # ----- 5. FREQ_HIGH -----
    # contributions by same donor to same candidate within window
    if donor_id and not all_transactions.empty: #only evalutes if donor_id exists
        window_start = tx_time - timedelta(hours = SUSPICIOUS_FREQ_WINDOW)

        #Filter historical data for matches on donor_id, candidate_id and timestamps
        recent = all_transactions[
            (all_transactions["donor_id"] == donor_id) &
            (all_transactions["candidate_id"] == candidate_id) &
            (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
        ]

        
        #Flag if frequency exceeds allowed limit
        if len(recent) >= SUSPICIOUS_FREQ_COUNT:
            reasons.append("FREQ_HIGH")
            explanations.append(
                f"Donor has made {len(recent)} donations to this candidate in the last"
                f"{SUSPICIOUS_FREQ_WINDOW} hours (threshold: {SUSPICIOUS_FREQ_COUNT})."
            )
    
    # -----6. MULTI_CANDIDATE_DONOR -----
    # contributions by same donor to different candidates within window
    if donor_id and not all_transactions.empty:
        window_start = tx_time - timedelta(hours = MULTI_CANDIDATE_WINDOW_HOURS)

        #Identify all candidates supported by this donor within timeframe
        recent_candidates = all_transactions[
            (all_transactions["donor_id"] == donor_id) &
            (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
        ]
        
        #Filter to unique candidates supported within the window
        num_unique_candidates= recent_candidates["candidate_id"].nunique()

        # Flag if they supported 3 or more different candidates within the window
        if num_unique_candidates >= 3:
            reasons.append("MULTI_CANDIDATE_DONOR")
            explanations.append(
                f"Donor has contributed to {num_unique_candidates} "
                f"within {MULTI_CANDIDATE_WINDOW_HOURS} hours."
            )

    # ----- 7. DISCLOSURE_REQUIRED -----
    #Compliance check: Does this single donation exceed the legal receipting limit?
    #Receipt likely complies with statutory financial regulations.
    if amount >= RECEIPT_THRESHOLD_KES:
        reasons.append("DISCLOSURE_REQUIRED")
        explanations.append(
            f"Donation of KES {amount:,.0f} exceeds the disclosure threshold of {RECEIPT_THRESHOLD_KES:,.0f}. Receipt required"
        ) 

    #----- STATUS CATEGORIES----- 
    #Group flags to deterime severity
    violation_codes = {"CAP_BREACH", "ILLEGAL_SOURCE", "PUBLIC_RESOURCE", "ANONYMOUS_DONATION"}
    suspicious_codes = {"MULTI_CANDIDATE_DONOR", "FREQ_HIGH"}

    #Check if any flags raised are in our lists
    has_violations = any(r in violation_codes for r in reasons)
    has_suspicious = any(r in suspicious_codes for r in reasons)

    #Priority logic
    if has_violations:
        status = "Violation"
    elif has_suspicious:
        status = "Suspicious"
    else:
        status = "Compliant"
    
    #Human-readable string. If reasons exi, join them otherwise use default text.
    explain = " ".join(explanations) if explanations else "Transaction meets all compliance requirements."

    #Return result as dict
    return {
        "reasons": reasons,
        "status": status,
        "explain": explain
    }

#Define enforcemment actions
def compute_enforcement(candidate_id: str, new_status: str, all_transactions: pd.DataFrame) -> str:
    """
    Computes enforcement action based on candidates history
    Returns: NONE, ON_HOLD, LOCKED, BANNED
    """
    
    #Current transaction has a violation             
    if new_status == "Violation":
        #Checks frequency of suspicious flags in days
        lock_window_start = datetime.now(timezone.utc)- timedelta(days=LOCK_WINDOW_DAYS)
        if not all_transactions.empty:
            #Check if the candidate has been locked before
            prior_locks = all_transactions[
                (all_transactions["candidate_id"] == candidate_id) &
                (all_transactions["enforcement_action"] == "LOCKED") &
                (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= lock_window_start)
                ]
            #If they have been locked before they are now banned
            if len(prior_locks)>= BAN_AFTER_LOCKS:
                return "BANNED"
        #Otherwise default to locked    
        return "LOCKED" 
    
    if new_status == "Suspicious":
        #Checks frequency of suspicious flags recently
        window_start = datetime.now(timezone.utc)- timedelta(hours=SUSPICIOUS_FREQ_WINDOW)

        #Only run if there is a history of transactions to look at
        if not all_transactions.empty:
            #Filter history to see how many times this candidate has been flagged recently
            recent_suspicious = all_transactions[
                (all_transactions["candidate_id"] == candidate_id) &
                (all_transactions["status"] == "Suspicious") &
                (pd.to_datetime(all_transactions["timestamp"], errors="coerce") >= window_start)
                ]
            
            #If they hit the limit put ON_HOLD
            if len(recent_suspicious)>= SUSPICIOUS_FREQ_COUNT :
                return "ON_HOLD"
    #Default if no rules are triggered        
    return "NONE"