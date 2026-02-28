"""
AI Investigation breif generator

Safe approach: deterministic, rule-driven, traces directly back to the rule engine
no black-box decisions, no external API calls

No change required if a real LLM is used since function signatures remain same
"""

from __future__ import annotations\

def generate_ai_explanation(transaction: dict, rule_result: dict) -> str:
    """
    Generates a plain lang investigative breif for flagged transactions.
    
    Args: transaction -> full transaction dict as stored in CSV.
          rule_result -> dict returned by  run_rules() in rules.py

    Returns:
         A string investigative brief (prose)      
    """

    #Extract feilds from run_rules in rules.py
    status = rule_result.get("status", "")
    reasons = rule_result.get("reasons", [])
    deadline = rule_result.get("escalation_deadline", "")

    #Build the memo into a list, then join
    memo = []
    memo.append("INVESTIGATION BRIEF (Auto - generated)")
    memo.append(f"Transaction: {transaction.get('transaction_id')} | Candidate: {transaction.get('candidate_is')} | Amount: KES {float(transaction.get('amount_kes',0)):,.0f}")
    memo.append(f"Assessment: {status}")
    memo.append(f"Triggered rules: {', '.join(reasons) if reasons else 'None'}")

    #Build a specific list of next steps based on which rules fired
    next_steps = []
    if "INCOMPLETE_RECORDS" in reasons or rule_result.get("missing_records"):
        next_steps.append("Request missing contributor and payment records (Section 26(1); Section 21(4)(b)).")
    if "ANONYMOUS_DONATION" in reasons or "ILLEGAL_SOURCE" in reasons:
        next_steps.append("Confirm donor identity/source; prepare IEBC submission within 14 days (Section 13(2)).")
    if "PUBLIC_RESOURCE" in reasons:
        next_steps.append("Verify any linkage to State/public resources; report within 48 hours(Section 14(3)) to avoid disqualification risk (Section14(4)).")
    if "CAP_BREACH" in reasons or "SINGLE_SOURCE_EXCEEDED" in reasons:
        next_steps.append("Validate whether the contribution should be rejected/refunded and recorded; check structured-donation attempts (Section12).")
    if "FREQ_HIGH" in reasons or "MULTI_CANDIDATE_DONOR" in reasons:
        next_steps.append("Review donor behaviour for coordination/structuring; examine related transactions within 24hr window.")
    
    #Default if no specific steps apply
    if not next_steps:
        next_steps.append("Maintain records; no additional action required.")
    
    memo.append("Recommended next steps:")
    for i, step in enumerate(next_steps, start=1):
        memo.append(f"  {i}. {step}")
    
    #Disclaimer - breif for review only
    memo.append("Note: This brief supports review; it does not determine guilty or liability.")

    #Join all lines with new lines to produce final string memo
    return "\n".join(memo)


