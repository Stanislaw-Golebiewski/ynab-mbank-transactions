from .models import Budget, Account, YNABTransaction, YNABTransactionInput, AddTransactionsResult
import requests
import json


class YNABApiClient:
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, auth_token):
        self.headers = {"Authorization": f"Bearer {auth_token}"}


    def get_budgets(self):
        """Retrieve a list of budgets."""
        url = f"{self.BASE_URL}/budgets"
        response = requests.get(url, headers=self.headers)
        raw_data = response.json()["data"]["budgets"]
        return [Budget(**budget) for budget in raw_data]


    def get_accounts(self, budget_id):
        """Retrieve a list of accounts for a given budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts"
        response = requests.get(url, headers=self.headers)
        raw_accounts = response.json()["data"]["accounts"]
        return [Account(**acct) for acct in raw_accounts]


    def get_balance(self, budget_id, account_id):
        """Retrieve the balance of a specific account within a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts/{account_id}"
        response = requests.get(url, headers=self.headers)
        data = response.json()
        return data.get("data", {}).get("account", {}).get("balance")


    def get_transactions(self, budget_id, account_id, since_date: str | None = None) -> list[YNABTransaction]:
        """Retrieve transactions for a specific account within a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts/{account_id}/transactions"
        params = {"since_date": since_date} if since_date else {}
        response = requests.get(url, headers=self.headers, params=params)
        raw_txns = response.json()["data"]["transactions"]
        return [YNABTransaction(**txn) for txn in raw_txns]

    def add_transactions(self, budget_id: str, account_id: str, transactions: list[YNABTransactionInput]) -> AddTransactionsResult:
        """Add new transactions to a budget."""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        payload = {
            "transactions": [json.loads(txn.model_dump_json(exclude_none=True)) for txn in transactions]
        }
        response = requests.post(url, json=payload, headers=self.headers)
        resp_json = response.json()

        if (data := resp_json.get('data')) is not None:
            transactions_list = data.get('transaction_ids', [])
            return AddTransactionsResult(
                is_success=True,
                number_of_transactions=len(transactions_list),
                transaction_ids=transactions_list
            )

        error_msg = resp_json.get('error', {}).get('detail', None)
        return AddTransactionsResult(
            is_success=False,
            error_msg=error_msg
        )
