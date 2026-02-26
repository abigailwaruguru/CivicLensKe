#CSV Storage 
import pandas as pd
import os
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRANSACTIONS_FILE = os.path.join(DATA_DIR,"civiclens_sample_transactions.csv")
CANDIDATE_STATE_FILE = os.path.join(DATA_DIR, "candidate_states.csv")
COMPLIANTS_FILE = os.path.join(DATA_DIR,"comlpiants.csv")

TRANSACTIONS_COLUMNS = [
    "transaction_id","timestamp","donor_id","donor_display","donor_source_type",
    "candidate_id","candidate_name","party","amount_kes","payment_method",
    "is_anonymous","is_public_resource","is_illegal_source","harambee_venue",
    "harambee_organiser","notes","reasons","status","explain", "enforcement_action"
]

CANDIDATE_STATE_COLUMNS = ["candidate_id", "state", "updated_at", "updated_by"]

COMPLIANTS_COLUMNS = [
    "compliant_id","transaction_id", "created_at", 
    "description", "notes", "status"
]

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok= True)

#Transactions
def load_transactions() -> pd.DataFrame:
    _ensure_dir()
    if not os.path.exists(TRANSACTIONS_FILE):
        return pd.DataFrame(columns= TRANSACTIONS_COLUMNS)
    
    




