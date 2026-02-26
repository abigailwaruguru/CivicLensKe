#CSV Storage 
import pandas as pd
import os
import uuid
from datetime import datetime

#File paths for CSV storage files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRANSACTIONS_FILE = os.path.join(DATA_DIR,"civiclens_sample_transactions.csv")
CANDIDATE_STATE_FILE = os.path.join(DATA_DIR, "candidate_states.csv")
COMPLIANTS_FILE = os.path.join(DATA_DIR,"comlpiants.csv")

#Expected columns for each CSV
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
#Ensure the data folder exists
def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok= True)

#TRANSACTIONS
# Load all transactions from csv into DataFrame
def load_transactions() -> pd.DataFrame:
    _ensure_dir()
    if not os.path.exists(TRANSACTIONS_FILE):
        return pd.DataFrame(columns= TRANSACTIONS_COLUMNS)
    try: 
        df = pd.read_csv(TRANSACTIONS_FILE, dtype=str)
        #If computed columns are missing, fill with default columns
        computed_defaults = {
            "status": "Compliant",
            "reasons": "",
            "explain": "",
            "enforcement_action": "NONE",
        }

        for col in TRANSACTIONS_COLUMNS:
            if col not in df.columns:
                df[col] = computed_defaults.get(col, "")
        return df[TRANSACTIONS_COLUMNS]
    except Exception: 
        return pd.DataFrame(columns=TRANSACTIONS_COLUMNS)
    
#Saving from DataFrame back to csv
def save_transactions(df: pd.DataFrame):
        _ensure_dir()
        df.to_csv(TRANSACTIONS_FILE, index= False)

#Add new transactions to the csv and fills missing feilds with defaults
def append_transaction(row: dict) -> pd.DataFrame:
     df = load_transactions()
     #Fil;l Defaults
     row.setdefault("transaction_id", "TXN-" + uuid.uuid4().hex[:8].upper())
     row.setdefault("timestamp", datetime.utcnow().isoformat())
     row.setdefault("donor_id", "")
     row.setdefault("donor_display", "Anonymous")
     row.setdefault("donor_source_type", "unknown")
     row.setdefault("party", "")
     row.setdefault("payment_method", "unknown")
     row.setdefault("is_anonymous", False)
     row.setdefault("is_public_resource", False)
     row.setdefault("is_illegal_source", False)
     row.setdefault("harambee_venue", "")
     row.setdefault("harambee_organiser","")
     row.setdefault("notes", "")
     row.setdefault("reasons", "")
     row.setdefault("status", "")
     row.setdefault("explain", "")
     row.setdefault("enforcement_action", "NONE")

     new_row = pd.DataFrame([{col: row.get(col, "") for col in TRANSACTIONS_COLUMNS}])
     df = pd.concat([df, new_row], ignore_index= True)
     save_transactions(df)
     return df

#Candidate States
def load_candidate_states() -> pd.DataFrame:
    _ensure_dir()
    if not os.path.exists(CANDIDATE_STATE_FILE):
        return pd.DataFrame(columns=CANDIDATE_STATE_COLUMNS)
    try:
        return pd.read_csv(CANDIDATE_STATE_FILE, dtype = str)
    except Exception:
        return pd.DataFrame(columns=CANDIDATE_STATE_COLUMNS)
    
def save_candidate_states(df: pd.DataFrame):
    _ensure_dir()
    df.to_csv(CANDIDATE_STATE_FILE, index= False)

#Check current enforcement state for a candidate and returns the account state
def get_candidate_state(candidate_id: str) -> str:
    """Returns ACTIVE, ON_HOLD, LOCKED, BANNED"""
    df = load_candidate_states()
    row = df[df["candidate_id"] == candidate_id]
    if row.empty: 
        return "ACTIVE"
    return str(row.iloc[-1]["state"])

#Update candidate state and log who updated it
def set_candidate_state(candidate_id: str, state: str, updated_by: str = "system"):
    df = load_candidate_states()
    new_row = pd.DataFrame([{
        "candidate_id": candidate_id,
        "state": state,
        "updated_by": updated_by,
        "updated_at": datetime.utcnow().isoformat(),
    }])
    df = df[df["candidate_id"] != candidate_id]
    df = pd.concat([df, new_row], ignore_index=True)
    save_candidate_states(df)

#Compliants
def load_compliants() -> pd.DataFrame:
    _ensure_dir()
    if not os.path.exists(COMPLIANTS_FILE):
        return pd.DataFrame(columns=COMPLIANTS_COLUMNS)
    try: 
        return pd.read_csv(COMPLIANTS_FILE, dtype=str)
    except Exception:
        return pd.DataFrame(columns= COMPLIANTS_COLUMNS)
    
def save_compliants(df: pd.DataFrame):
    _ensure_dir()
    df.to_csv(COMPLIANTS_FILE, index=False)

#Save a new complaint and generate unique Compliant ID
def append_compliant(row: dict) -> dict:
    df = load_compliants()
    row["compliant_id"] = "CMP-" + uuid.uuid4().hex[:8].upper()
    row["created_at"] = datetime.utcnow().isoformat()
    row.setdefault("status", "open")
    row.setdefault("notes", "")
    new_row = pd.DataFrame([{col: row.get(col, "") for col in COMPLIANTS_COLUMNS}])
    df = pd.concat([df, new_row], ignore_index=True)
    save_compliants(df)
    return row