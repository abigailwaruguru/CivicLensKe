#Report generation

import io 
import pandas as pd
from storagecsv import load_transactions, load_compliants

REGULATOR_COLUMNS = [
    "transaction_id", "timestamp", "candidate_id", "candidate_name",
    "party", "donor_display", "amount_kes", "status", "reasons","explain",
    "enforcement_action",
]


def generate_regulator_pack_csv() -> bytes:
    """
    Returns CSV bytes of all Suspicious and Violation transactions
    with enforcement actions - safe for regulator export (masked donor display).
    """

    df = load_transactions()
    if df.empty:
        flagged = pd.DataFrame(columns=REGULATOR_COLUMNS)
    else:
        flagged = df[df["status"].isin(["Suspicious", "Violation", "Rejected_Locked"])]
        #Only keep safe columns (donor_display is already masked)
        for col in REGULATOR_COLUMNS: 
            if col not in flagged.columns:
                flagged[col] = ""
            flagged = flagged[REGULATOR_COLUMNS]

    output = io.StringIO()
    flagged.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")


def generate_case_file_csv(compliant_id: str = None) -> bytes:
    """
    Returns a CSV case file. If compliant_id is provided, filters to transaction linked to that complaint. 
    """
    df_tx = load_transactions()
    df_complaints = load_compliants()

    if complaint_id:
        compliant_row = df_compliants[df_compliants["compliant_id"] == compliant_id]
        if compliant_row.empty:
            return b"compliant_id not found"
        linked_ids_str = complaint_row.iloc[0].get("transaction_ids", "")