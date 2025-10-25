from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import date, datetime


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "creditCard"
    cash = "cash"
    line_of_credit = "lineOfCredit"
    other_asset = "otherAsset"
    other_liability = "otherLiability"
    mortgage = "mortgage"
    investment_account = "investmentAccount"
    student_loan = "studentLoan"
    car_loan = "carLoan"
    personal_loan = "personalLoan"
    medical_debt = "medicalDebt"

class Budget(BaseModel):
    id: str
    name: str
    first_month: date
    last_month: date
    last_modified_on: datetime


class Account(BaseModel):
    id: str
    name: str
    type: AccountType
    balance: int
    cleared_balance: int
    uncleared_balance: int
    on_budget: bool
    closed: bool
    last_reconciled_at: Optional[datetime]


class BankTransaction(BaseModel):
    date: date
    amount: int
    description: str

    def __hash__(self):
        return hash((self.date, self.amount))


class YNABTransaction(BaseModel):
    id: str
    date: date
    amount: int
    memo: Optional[str]
    cleared: str
    approved: bool
    payee_name: Optional[str]
    category_name: Optional[str]
    deleted: bool

    def __hash__(self):
        return hash((self.date, self.amount))


class YNABTransactionInput(BaseModel):
    account_id: str
    date: date
    amount: int
    cleared: str = "uncleared"
    approved: bool = False
    payee_id: Optional[str] = None
    payee_name: Optional[str] = None
    category_id: Optional[str] = None
    memo: Optional[str] = None
    import_id: Optional[str] = None


class AddTransactionsResult(BaseModel):
    is_success: bool
    number_of_transactions: int | None = None
    transaction_ids: list[str] | None = None
    error_msg: str | None = None

