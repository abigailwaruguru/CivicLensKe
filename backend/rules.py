#Rule engine: Defining Rules based on 
#Kenya Election Campaign Financing Act
import pandas as pd
from datetime import datetime, timedelta, timezone

#Constants
#Max contribution limit - to be prescribed by IEBC
CAP_KES = 500_000
#Single source donation limit - 20%
SINGLE_SOURCE_LIMIT = 20
#Total spending limit per candidate
SPENDING_LIMIT_KES = 2_000_000

#Anonymous/illegal donations reported within 14 days
ANONYMOUS_REPORT_WINDOW_DAYS = 14
#Public resource donations reported within 48 hours
PUBLIC_RESOURCE_REPORT_WINDOW_HOURS = 48

#Complaint resolved within 7 days before election
COMPLAINT_WINDOW_BEFORE_ELECTION_DAYS = 7
#Complaint resolved within 14 days before election
COMPLAINT_WINDOW_AFTER_ELECTION_DAYS = 14

#Auto-generate receipt above this amount
RECEIPT_THRESHOLD_KES = 20_000

#Same window apply to claims and objections
CLAIM_WINDOW_BEFORE_ELECTION_DAYS = 7
CLAIM_WINDOW_AFTER_ELECTION_DAYS =14

#Frequency monitoring thresholds
SUSPICIOUS_FREQ_COUNT = 3
SUSPICIOUS_FREQ_WINDOW = 12
MULTI_CANDIDATE_WINDOW_HOURS = 24 #Window for multi-candiate donor check

#Enforcement thresholds
LOCK_WINDOW_DAYS = 30 #Window for counting locks
BAN_AFTER_LOCKS = 2 #Locks within window before BAN

#Required record feilds for financial accountability
REQUIRED_RECORD_FEILDS = ["donor_id", "donor_display", "donor_source_type", "amount_kes", "payment_method"]

def _parse_bool(val) -> bool:
    #Converts to python bool
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)

def get_compliant_deadline(is_before_election: bool, filed_at: datetime = None) -> str:
    """
    Compute compliant/ claim resolution deadline.
    Returns ISO format deadline string.
    """
    if filed_at is None:
        filed_at = datetime.now(timezone.utc)
    days = COMPLAINT_WINDOW_BEFORE_ELECTION_DAYS if is_before_election else COMPLAINT_WINDOW_AFTER_ELECTION_DAYS
    deadline = filed_at + timedelta(days=days)
    return deadline.strftime("%Y-%m-%dT%H:%M:%S")

#Rule Engine
#Define function to check new transaction against all past Transactions
def run_rules(transaction: dict, all_transactions: pd.DataFrame) -> dict:
    """
    Compares a new transaction against historical data to run compliance checks.
    Also follows the Kenya Election Campaign Financing Act rules for evaluation criteria
    Returns: dict with outcome reasons: [str], status: str, explain: [str], 
    escalation_required, escalation_deadline, receipt_required
    """
    #Initializes lists to store rule violations and explantaions
    reasons = []
    explanations = []
    escalation_required = False
    escalation_deadline = ""
    receipt_required = False
    
    #IEBC enforcement orders that apply to this transaction
    #These mirror the actual orders the IEBC can issue under the Act
    iebc_orders = []

    #Track missing required record files
    missing_records = []

    #Get aspects of the new transaction that are to be cross checked
    #Defaults any missing to avoid errors
    amount = float(transaction.get("amount_kes", 0))
    donor_id = transaction.get("donor_id", "")
    candidate_id  = transaction.get("candidate_id", "")
    donor_source_type = transaction.get("donor_source_type", "unknown")
    ts = transaction.get("timestamp", datetime.now(timezone.utc).isoformat())

    #Convert to date time format for python to do calculation of frequencies
    try:
        tx_time = datetime.fromisoformat(ts)
        if tx_time.tzinfo is None:
            tx.time = tx.time.replace(tzinfo=timezone.utc)
    except Exception:
        tx_time = datetime.now(timezone.utc)

    #Rule check declarations to determine return results (dict values)
    # ----- 1. CAP BREACH -----
    if amount> CAP_KES:
        reasons.append("CAP_BREACH")
        explanations.append(
            f"Donation of KES {amount:,.0f} exceeds the contribution "
            f"cap of KES {CAP_KES:,.0f} prescribed under Section 12(1) of the Act."
        )
        #IEBC fine applicable and disqualification
        iebc_orders.append("Section 21(5)(c): Fine applicable")
        iebc_orders.append("Section 21(5)(f): Fine applicable")

    # ----- 2.SINGLE_SOURCE_EXCEED -----
    if donor_id and not all_transactions.empty:
        candiadte_txs = all_transactions[all_transactions["candidate_id"] == candidate_id]
        total_received = candiadte_txs["amount_kes"].astype(float).sum()
        new_total = total_received + amount
        if new_total > 0:
            donor_total = candiadte_txs[
                candiadte_txs["donor_id"] == donor_id
            ]["amount_kes"].astype(float).sum() +amount
            donor_share_percent = (donor_total / new_total) * 100
            if donor_share_percent > SINGLE_SOURCE_MAX_PERCENT:
                reasons.append("SINGLE_SOURCE_EXCEED")
                explanations.append(
                    f"Donor contributions to this candidate would reach"
                    f"KES {donor_total:,.0f} - {donor_share_percent:,.0f}% of total. "
                    f"Section 12(2) limits a single source to {SINGLE_SOURCE_LIMIT}% of total contribution. "
                )
                iebc_orders.appendd("Section 21(5)(b): Formal warning")
                iebc_orders.append("Section 21(5)(c): Fine applicable")
            
    # ----- 3. SPENDING_LIMIT_BREACH -----  
    if not all_transactions.empty:
        candidate_total = all_transactions[
            all_transactions["candidate_id"] == candidate_id
        ]["amount_kes"].astype(float).sum()
        if candidate_total + amount > SPENDING_LIMIT_KES:
            reasons.append("SPENDING_LIMIT_BREACH")
            explanations.append(
                f"Total donations to this candidate would reach "
                f"KES {candidate_total + amount:,.0f}, exceeding the spending limit "
                f"of KES {SPENDING_LIMIT_KES:,.0f} under Section 18. "
            )
            iebc_orders.append("Section 21(5)(c): Fine up to KES 2,000,000")
            iebc_orders.append("Section 23(3): Disqualification from election")

    # ----- 4. ANONYMOUS_DONATION -----
    if _parse_bool(transaction.get("is_anonymous", False)):
        reasons.append("ANONYMOUS_DONATION")
        explanations.append(
            "Donor is unknown. Prohibited under Section 13(1)(a). "
            f"Must be reported to IEBC within {ANONYMOUS_REPORT_WINDOW_DAYS} days per Section 13(2). "
            "Failure to report is an offence under Section 13(3)."
        )
        escalation_required = True
        deadline = tx_time +timedelta(days = ANONYMOUS_REPORT_WINDOW_DAYS)
        escalation_deadline = deadline.strftime("%Y-%m-%dT%H:%M:%S")
        iebc_orders.append("Section 21(5)(a): Rectification of records required")
        iebc_orders.append("Section 21(5)(f): Possible disqualification")
        
    # ----- 5. ILLEGAL_SOURCE -----
    if _parse_bool(transaction.get("is_illegal_source",False)):
        reasons.append("ILLEGAL_SOURCE")
        explanations.append(
            "Contribution is from an illegal/prohibited source under Section 13(1)(b). "
            f"Must be reported to IEBC within {ANONYMOUS_REPORT_WINDOW_DAYS} days per Section 13(2). "
            "Failure to report is an offence under Section 13(3)."
        )
        escalation_required = True
        if not escalation_deadline:
            deadline = tx_time + timedelta(days = ANONYMOUS_REPORT_WINDOW_DAYS)
            escalation_deadline = deadline.strftime("%Y-%m-%dT%H:%M:%S")
        iebc_orders.append("Section 21(5)(a): Rectification of records required")
        iebc_orders.append("Section 21(5)(c): Fine applicable")

    # ----- 6. PUBLIC_RESOURCE -----
    if _parse_bool(transaction.get("is_public_resource",False)):
        reasons.append("PUBLIC_RESOURCE")
        explanations.append(
            "Suspected use of State or Public resources"
            f"Must be reported to IEBC within  {PUBLIC_RESOURCE_REPORT_WINDOW_HOURS} hours per Section 14(3). "
            "Failure to report leads to disqualification under Section 14(4)."
        )
        escalation_required = True
        deadline = tx_time + timedelta(hours=PUBLIC_RESOURCE_REPORT_WINDOW_HOURS)
        escalation_deadline = deadline.strftime("%Y-%m-%dT%H:%M:%S")
        #Automatic disqualification for non-reporting
        iebc_orders.append("Section 14(4): Disqualification if not reported")
        iebc_orders.append("Section 21(5)(d): Campaign prohibited order")

    # ----- 7. UNREGISTERED_ORG_RISK -----
    if donor_source_type == "organisation":
        reasons.append("UNREGISTERED_ORG_RISK")
        explanations.append(
            "Section 15(2)(b) requires organisations to register with IEBC before contributing."
            "Registration cannot be verified automatically - manual review required. "
        )
        iebc_orders.append("Section 21(5)(b): Formal warning - pending verification")

    # ----- 8. FREQ_HIGH -----
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
                "Pattern suggests sructured donations to circumvent caps - "
                "may constitute false reporting under Section 22(e)."
            )
            iebc_orders.append("Section 21(5)(b): Formal warning")
    
    # -----9. MULTI_CANDIDATE_DONOR -----
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
                "Pattern suggests coordinated political financing. "
                "Section 26(1) requires full contributor records for investigation."
            )
            iebc_orders.append("Section 21(4)(b): IEBC may call for contributor records")

    # ----- 10. DISCLOSURE_REQUIRED -----
    #Compliance check: Does this single donation exceed the legal receipting limit?
    #Receipt likely complies with statutory financial regulations.
    if amount >= RECEIPT_THRESHOLD_KES:
        receipt_required = True
        reasons.append("DISCLOSURE_REQUIRED")
        explanations.append(
            f"Donation of KES {amount:,.0f} exceeds KES {RECEIPT_THRESHOLD_KES:,.0f}. "
            "Receipt must be issued under Section 16(1). "
            "Failure to disclose is an offence under Section 16(6). "
            "Record of the amount and nature of funds received are also required under Section 26(1)(a)"
        ) 

    # ----- 11. HARAMBEE_INCOMPLETE -----
    if donor_source_type == "harambee":
        venue = transaction.get("harambee_venue", "").strip()
        organiser = transaction.get("harambee_organiser", "").strip()
        if not venue or not organiser:
            reasons.append("HARAMBEE_INCOMPLETE")
            explanations.append(
                "Harambee contribution missing required details. "
                "Section 16(2) requires venue, date, organiser, and total contributions. "
                "Incomplete harambee records are an offence under Section 16(6)."
            )
            iebc_orders.append("Section 21(5)(a): Rectification of harambee records required")

    # ----- 12. INCOMPLETE_RECORDS -----
    # sECTION 26(1) - Records must include amount, nature, and contributor details
    for field in REQUIRED_RECORD_FEILDS:
        val = transaction.get(field, "")
        if not val or str(val).strip() in ("", "unknown", "None"):
            missing_records.append(field)

        if missing_records:
            reasons.append("INCOMPLETE_RECORDS")
            explanations.append(
                f"Transaction id missing required feilds: {', '.join(missing_records)}. "
                "Section 26(1) requires full records of funds received. "
                "Section 22(b) makes refusal to produce records an offence."
            )
            iebc_orders.append("Section 21(4)(b): IEBC may call for missing records")

    
    # ----- 13. FALSE_INFROMATION_RISK -----
    #Flags if donor_display says Anonymous but is_anonymous is false
    #This could indicate knowingly false information per Section 22(d)
    donor_display = transaction.get("donor_display", "").strip().lower()
    is_anonymous = _parse_bool(transaction.get("is_anonymous", False))
    if donor_display in ("anonymous", "") and not is_anonymous and donor_id == "":
        reasons.append("FALSE_INFO_RISK")
        explanations.append(
            "Donor display name suggests anonymous but is_anonymous flag is false and no donor ID provided. "
            "This inconsistency may constitute knowingly giving false information "
            "Section 22(d) - liable to KES 2,000,000 fine or 5 years imprisonment."
        )
        iebc_orders.append("Section 21(5)(c): Fine up to KES 2,000,000")

        
    #----- STATUS CATEGORIES----- 
    #Group flags to deterime severity
    violation_codes = {
        "CAP_BREACH", "ILLEGAL_SOURCE", "PUBLIC_RESOURCE", "ANONYMOUS_DONATION",
        "SPENDING_LIMIT_BREACH", "SINGLE_SOURCE_EXCEEDED", "FALSE_INFO_RISK"
        }
    suspicious_codes = {
        "MULTI_CANDIDATE_DONOR", "FREQ_HIGH", "UNREGISTERED_ORG_RISK",
        "HARAMBEE_INCOMPLETE", "INCOMPLETE_RECORDS"
        }

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
    explain = " | ".join(explanations) if explanations else (
        "Transaction meets all compliance requirements"
        "under the Kenya Campaign Financing Act."
    )

    #Return result as dict
    return {
        "reasons": reasons,
        "status": status,
        "explain": explain,
        "escalation_required": escalation_required,
        "escalation_deadline": escalation_deadline,
        "receipt_required": receipt_required,
        "iebc_orders": iebc_orders,
        "missing_records": missing_records
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