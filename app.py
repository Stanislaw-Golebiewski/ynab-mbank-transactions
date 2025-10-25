import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from loguru import logger
from ynab.api_client import YNABApiClient
from ynab.importers import load_bank_transactions_from_file
from ynab.models import (
    AddTransactionsResult,
    BankTransaction,
    YNABTransaction,
    YNABTransactionInput,
)
from ynab.resolver import reconcile_transactions

load_dotenv()

# Constants
BUDGET_ID = os.getenv("YNAB_BUDGET_ID")
ACCOUNT_ID = os.getenv("YNAB_ACCOUNT_ID")

if BUDGET_ID is None:
    raise ValueError("YBAB_BUDGET_ID env var has to be set")

if ACCOUNT_ID is None:
    raise ValueError("YBAB_ACCOUNT_ID env var has to be set")


def main():
    st.title("YNAB Transaction Sync")

    if "ynab_transactions" not in st.session_state:
        st.session_state.ynab_transactions = None
        st.session_state.ynab_balance = None

    if "reconciliation_success" not in st.session_state:
        st.session_state.reconciliation_success = False
        st.session_state.reconcile_result = None

    # Fetch YNAB Transactions
    if st.button("Fetch YNAB Transactions"):
        with st.spinner("Fetching YNAB data..."):
            token = os.getenv("YNAB_ACCESS_TOKEN")
            if not token:
                st.error("YNAB_ACCESS_TOKEN not found in environment!")
                return
            client = YNABApiClient(auth_token=token)
            st.session_state.client = client

            try:
                transactions = client.get_transactions(BUDGET_ID, ACCOUNT_ID)
                balance = client.get_balance(BUDGET_ID, ACCOUNT_ID)
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                st.error(f"Error fetching data: {e}")
                return

            st.session_state.ynab_transactions = transactions
            st.session_state.ynab_balance = balance

            non_reconciled = [t for t in transactions if t.cleared != "reconciled"]
            latest_date = max(t.date for t in transactions) if transactions else "N/A"

            st.success("YNAB data loaded successfully!")
            st.markdown(f"- **Total transactions:** {len(transactions)}")
            st.markdown(f"- **Non-reconciled:** {len(non_reconciled)}")
            st.markdown(f"- **Latest transaction date:** {latest_date}")
            st.markdown(f"- **YNAB account balance:** {balance / 1000:.2f} zł")

    # Upload and process bank transactions
    if st.session_state.ynab_transactions is not None:
        st.markdown("---")
        st.subheader("Upload Bank CSV and Enter Balance")

        with st.form("bank_form"):
            csv_file = st.file_uploader("Upload bank CSV file", type=["csv"])
            bank_balance_float = st.number_input(
                "Current bank balance", min_value=0.0, step=0.01
            )
            submitted = st.form_submit_button("Run Sync")
        if submitted:
            if csv_file is None or bank_balance_float == 0.0:
                st.warning("Please upload a file and enter a balance.")
            else:
                with st.spinner("Processing..."):
                    try:
                        bank_transactions, _ = load_bank_transactions_from_file(
                            csv_file
                        )
                        bank_balance_milli = int(bank_balance_float * 1000)

                        result = reconcile_transactions(
                            bank_transactions=bank_transactions,
                            ynab_transactions=st.session_state.ynab_transactions,
                            current_bank_balance=bank_balance_milli,
                            current_ynab_balance=st.session_state.ynab_balance,
                            account_id=ACCOUNT_ID,
                        )

                        st.session_state.reconcile_result = result
                        st.session_state.reconciliation_success = result[
                            "reconciliation_possible"
                        ]

                        if result["reconciliation_possible"]:
                            st.success("✅ Reconciliation is possible!")
                        else:
                            st.error("❌ Reconciliation not possible.")
                            st.markdown(
                                f"**Difference in balance:** {result['balance_delta'] / 1000:.2f} zł"
                            )

                        st.markdown(f"**To Add:** {len(result['to_add'])}")
                        st.markdown(f"**To Delete:** {len(result['to_delete'])}")
                        st.markdown(f"**To Keep:** {len(result['to_keep'])}")

                    except Exception as e:
                        st.error(f"Error processing bank transactions: {e}")
                        raise e

    # Show "Finalize Sync" button if reconciliation is successful
    if st.session_state.reconciliation_success:
        st.divider()
        transactions_to_add = st.session_state.reconcile_result["to_add"]
        transactions_to_delete = st.session_state.reconcile_result["to_delete"]

        if transactions_to_delete:
            st.warning(
                "NOTE: I will not be able to delete transactions, as it is not implemented yet :("
            )
        if st.button("Run sync"):
            with st.spinner("Adding new transactions..."):
                try:
                    result = st.session_state.client.add_transactions(
                        BUDGET_ID, ACCOUNT_ID, transactions_to_add
                    )
                    st.success("✅ Sync completed successfully!")
                    st.session_state.reconciliation_success = (
                        False  # Reset after completion
                    )
                except Exception as e:
                    st.error(f"Error during sync: {e}")


if __name__ == "__main__":
    main()
