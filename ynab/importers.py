import csv
import re
from datetime import datetime
from enum import StrEnum, auto
from io import BytesIO

from loguru import logger

from .models import BankTransaction


def _get_date_from_title_field(field: str) -> datetime | None:
    match = re.search(r"DATA\s+TRANSAKCJI:\s*(\d{4}-\d{2}-\d{2})", field)
    print(field, match)
    if match:
        date_str = match.group(1)
        transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return transaction_date

    return None


class FileSource(StrEnum):
    WEB_APP = auto()
    MOBILE_APP = auto()


def get_transaction_lines_from_csv(file: BytesIO) -> tuple[list[str], str, FileSource]:
    """Get transaction lines from file.

    This method anticipates 2 types of files:
    * UTF-8 encoded which was generated in MBank web application
    * CP1250 encoded which was generated in the mobile app
    """
    try:
        all_csv_lines = file.getvalue().decode("utf-8")
        file_type = FileSource.WEB_APP
    except UnicodeDecodeError:
        logger.info(
            "Failed to read file contents with UTF-8 encoding assumption - trying cp1250 encoding instead"
        )
        all_csv_lines = file.getvalue().decode("cp1250")
        file_type = FileSource.MOBILE_APP

    # Skip all unnecessary lines at the beginning
    csv_lines_filtered = []
    header_seen = False
    skipped_lines = 0
    final_saldo_line = None
    for idx, line in enumerate(all_csv_lines.split("\n")):
        if "#Data operacji" in line:
            csv_lines_filtered.append(line)
            header_seen = True
            continue

        if "#Saldo końcowe" in line:
            final_saldo_line = line
            break

        if header_seen:
            csv_lines_filtered.append(line)
        else:
            skipped_lines += 1

    logger.debug(
        f"Loaded lines from file: {len(csv_lines_filtered)} lines loaded, {skipped_lines} skipped. File type: {file_type}, has saldo line: {final_saldo_line is not None}."
    )
    if file_type == FileSource.WEB_APP:
        if skipped_lines == 37:
            file_type = FileSource.MOBILE_APP
    return csv_lines_filtered, final_saldo_line, file_type


def _parse_money_value_cell(cell: str) -> int:
    return float(cell.removesuffix(" PLN").replace(",", ".").replace(" ", ""))


def _get_description_for_mobile_case(parsed_record: dict) -> str:
    if parsed_record["#Nadawca/Odbiorca"].strip():
        out = parsed_record["#Nadawca/Odbiorca"].strip()
    else:
        out = parsed_record["#Tytuł"].split("/")[0].strip()
    return out


def _get_description_for_webapp_case(parsed_record: dict) -> str:
    return parsed_record["#Opis operacji"].split("  ")[0]


def load_bank_transactions_from_file(
    file: BytesIO,
) -> tuple[list[BankTransaction], int | None]:
    """Load transactions from MBank csv format."""

    out: list[BankTransaction] = []
    csv_lines, saldo_line, file_type = get_transaction_lines_from_csv(file)
    for parsed_line in csv.DictReader(csv_lines, delimiter=";"):
        if parsed_line["#Kwota"] == "":
            logger.debug("Skiping empty amount line...")
            continue

        clean_description = (
            _get_description_for_webapp_case(parsed_line)
            if file_type == FileSource.WEB_APP
            else _get_description_for_mobile_case(parsed_line)
        )
        clean_amount = _parse_money_value_cell(parsed_line["#Kwota"])

        date = None
        if file_type == FileSource.MOBILE_APP:
            date = _get_date_from_title_field(parsed_line["#Tytuł"])

        if date is None:
            date = datetime.strptime(parsed_line["#Data operacji"], "%Y-%m-%d")

        transaction = {
            "date": date,
            "amount": int(clean_amount * 1000),  # Conform to YNAB format
            "description": clean_description,
        }
        out.append(BankTransaction(**transaction))
    logger.info(f"Loaded {len(out)} lines from file. File type decetcted: {file_type}")
    if saldo_line:
        final_money_on_account = _parse_money_value_cell(
            saldo_line.removesuffix(";").split(";")[-1]
        )
        logger.info("Also decected final account saldo!")
        return out, final_money_on_account
    return out, None
