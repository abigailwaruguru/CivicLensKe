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
    if transaction.get("is.anonymous", False):
        reasons.append("ANONYMOUS_DONATION")
        explanations.append("Donor is unknown. Anonymous donations are prohibited")

    #3. ILLEGAL_SOURCE
    if transaction.get("is")
