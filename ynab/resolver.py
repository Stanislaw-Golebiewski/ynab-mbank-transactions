from datetime import date, timedelta
from math import floor
from typing import TypedDict

from .models import BankTransaction, YNABTransaction, YNABTransactionInput


class ReconcileTransactionResult(TypedDict):
    to_keep: set[YNABTransaction]
    to_delete: set[YNABTransaction]
    to_add: set[YNABTransactionInput]
    reconciliation_possible: bool
    balance_delta: int


def reconcile_transactions(
    bank_transactions: list[BankTransaction],
    ynab_transactions: list[YNABTransaction],
    current_bank_balance: int,  # e.g., 1234560 (milliunits)
    current_ynab_balance: int,  # e.g., 1234560 (milliunits)
    account_id: str,
    cutoff_days: int = 3,
) -> ReconcileTransactionResult:
    """
    Compare YNAB and bank transactions to determine:
    - Which to keep
    - Which to delete
    - Which to add
    - Whether reconciliation is possible

    Returns a dict with the reconciliation plan.
    """

    # 1. Split YNAB transactions
    reconciled = [t for t in ynab_transactions if t.cleared == "reconciled"]
    non_reconciled = [t for t in ynab_transactions if t.cleared != "reconciled"]

    print(
        f"Debug: non-reconsiled transactions in YNAB: {len(non_reconciled)}/{len(ynab_transactions)}"
    )

    # 2. Determine cutoff date
    if non_reconciled:
        min_ynab_date = min(t.date for t in non_reconciled)
    else:
        min_ynab_date = max((t.date for t in reconciled), default=date.today())
    cutoff_date = min_ynab_date - timedelta(days=cutoff_days)

    print(f"Debug: cutoff date {min_ynab_date}")

    # 3. Classify non-reconciled YNAB transactions
    to_keep = []
    to_delete = []

    for yt in non_reconciled:
        match = any(
            bt.date == yt.date and bt.amount == yt.amount for bt in bank_transactions
        )
        # match = yt in set(bank_transactions)
        if match:
            to_keep.append(yt)
        else:
            to_delete.append(yt)

    print(f"Debug: {len(to_keep)=} | {len(to_delete)=}")

    # 4. Detect new bank transactions not yet in YNAB
    already_recorded = {(t.date, t.amount) for t in reconciled + to_keep}
    bank_recent = [bt for bt in bank_transactions if bt.date >= cutoff_date]

    to_add = []
    for bt in bank_recent:
        if (bt.date, bt.amount) not in already_recorded:
            to_add.append(
                YNABTransactionInput(
                    account_id=account_id,
                    date=bt.date,
                    amount=bt.amount,
                    payee_name=bt.description,
                    cleared="uncleared",
                    approved=False,
                )
            )

    # 5. Calculate adjusted balance
    adjusted_balance = current_ynab_balance
    adjusted_balance -= sum(t.amount for t in to_delete)
    adjusted_balance += sum(t.amount for t in to_add)

    sum_to_delete = sum(t.amount for t in to_delete)
    sum_to_add = sum(t.amount for t in to_add)
    print(f"Debug: {adjusted_balance=} | {sum_to_delete=} | {sum_to_add}")
    delta = adjusted_balance - current_bank_balance
    reconciliation_possible = floor(adjusted_balance / 10) * 10 == current_bank_balance

    return {
        "to_keep": to_keep,
        "to_delete": to_delete,
        "to_add": to_add,
        "reconciliation_possible": reconciliation_possible,
        "balance_delta": delta,
    }
