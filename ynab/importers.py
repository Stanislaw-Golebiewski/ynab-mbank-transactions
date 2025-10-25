import csv
from datetime import datetime
from enum import StrEnum, auto
from io import BytesIO

from loguru import logger

from .models import BankTransaction


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
            print(line)
        else:
            skipped_lines += 1

    logger.debug(
        f"Loaded lines from file: {len(csv_lines_filtered)} lines loaded, {skipped_lines} skipped. File type: {file_type}, has saldo line: {final_saldo_line is not None}."
    )
    return csv_lines_filtered, final_saldo_line, file_type


def _parse_money_value_cell(cell: str) -> int:
    return float(cell.removesuffix(" PLN").replace(",", ".").replace(" ", ""))


def load_bank_transactions_from_file(file: BytesIO) -> list[BankTransaction]:
    """Load transactions from MBank csv format."""

    out: list[BankTransaction] = []
    csv_lines, saldo_line, file_type = get_transaction_lines_from_csv(file)

    for parsed_line in csv.DictReader(csv_lines, delimiter=";"):
        clean_description = parsed_line["#Opis operacji"].split("  ")[0]
        clean_amount = _parse_money_value_cell(parsed_line["#Kwota"])
        transaction = {
            "date": datetime.strptime(parsed_line["#Data operacji"], "%Y-%m-%d"),
            "amount": int(clean_amount * 1000),  # Conform to YNAB format
            "description": clean_description,
        }
        out.append(BankTransaction(**transaction))
    logger.info(f"Loaded {len(out)} lines from file. File type decetcted: {file_type}")
    if saldo_line:
        final_money_on_account = _parse_money_value_cell(saldo_line.split(";")[-2])
        logger.info("Also decected final account saldo!")
        return out, final_money_on_account
    return out, None
