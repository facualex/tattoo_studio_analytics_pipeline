"""
sheets_extractor.py

Ingestion layer module (ingest/) responsible for extracting the sheets from
the business' financial Google Sheets (tattoos, art, makeup, expenses and
withdrawals) and persisting them locally as Parquet files in data/tmp/,
with structured logging to console and file.

Scope: authentication + reading Google Sheets + writing local Parquet
files + logging. Does not include uploading to S3 or data transformation.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

# Loads the variables defined in the .env file (searches the current
# directory and parent directories) into the process environment.
load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Minimum scopes required: read Sheets and read Drive metadata
# (gspread uses Drive to resolve the spreadsheet by ID).
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Module base directory, used to anchor output directories regardless of
# the current working directory the script is invoked from.
BASE_DIR = Path(__file__).resolve().parent

# Module output directories.
DATA_DIR = Path("data/tmp")
LOGS_DIR = BASE_DIR / "logs"

# ---------------------------------------------------------------------------
# Logging configuration (console + file)
# ---------------------------------------------------------------------------

LOGS_DIR.mkdir(parents=True, exist_ok=True)

_run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
_log_file_path = LOGS_DIR / f"sheets_extractor_{_run_timestamp}.log"

logger = logging.getLogger("sheets_extractor")
logger.setLevel(logging.INFO)

_log_format = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_log_format)

_file_handler = logging.FileHandler(_log_file_path, encoding="utf-8")
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(_log_format)

logger.addHandler(_console_handler)
logger.addHandler(_file_handler)


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _normalize_sheet_name(sheet_name: str) -> str:
    """
    Normalizes a sheet name for use as a file name.

    Strips emojis and non-alphanumeric characters, lowercases the result,
    and replaces spaces with underscores.

    Args:
        sheet_name: original sheet name (may include emojis, e.g.
            "🖋️ Tatuajes").

    Returns:
        str: normalized name suitable for a file, e.g. "tatuajes".
    """
    normalized_chars = [char for char in sheet_name if char.isalnum() or char.isspace()]
    normalized = "".join(normalized_chars).strip().lower()
    return "_".join(normalized.split())


def _get_gspread_client() -> gspread.Client:
    """
    Creates and returns an authenticated gspread client using a Google
    Cloud Service Account.

    Credentials are read from the JSON file pointed to by the
    GOOGLE_CREDENTIALS_PATH environment variable.

    Returns:
        gspread.Client: authenticated client ready to open spreadsheets.
    """
    credentials = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )
    return gspread.authorize(credentials)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def extract_sheet(sheet_name: str, header_row: int) -> pd.DataFrame:
    """
    Extracts a specific sheet from the financial Google Sheets and returns
    it as a pandas.DataFrame.

    Authenticates against the Google Sheets API via a Service Account,
    opens the spreadsheet identified by SPREADSHEET_ID, selects the sheet
    by exact name, and builds the DataFrame using the header_row row as
    column headers and the following rows as data. Completely empty rows
    are discarded.

    Args:
        sheet_name: exact name of the sheet within the spreadsheet
            (e.g. "🖋️ Tatuajes").
        header_row: row number (1-indexed, as in Google Sheets) where the
            column headers are located.

    Returns:
        pandas.DataFrame: sheet data, with columns based on header_row.

    Raises:
        Propagates any exception raised during authentication, opening
        the spreadsheet/sheet, or reading values (e.g.
        gspread.exceptions.WorksheetNotFound, network or authentication
        errors). Handling/logging these exceptions is the caller's
        responsibility (see extract_all_sheets).
    """
    logger.info("Starting extraction of sheet '%s'", sheet_name)

    client = _get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(sheet_name)

    all_values = worksheet.get_all_values()

    headers = all_values[header_row - 1]
    data_rows = all_values[header_row:]

    # Discard completely empty rows (all cells blank).
    data_rows = [row for row in data_rows if any(cell.strip() for cell in row)]

    dataframe = pd.DataFrame(data_rows, columns=headers)

    logger.info(
        "Extraction finished for sheet '%s': %d rows extracted",
        sheet_name,
        len(dataframe),
    )

    return dataframe


def extract_all_sheets(sheet_configs: list[dict]) -> dict:
    """
    Orchestrates the extraction of multiple sheets and persists each one
    as a local Parquet file in data/tmp/.

    For each sheet configuration, calls extract_sheet(). If the
    extraction of a sheet fails, the error is logged (with traceback)
    and execution continues with the next sheet in the list; the failure
    of an individual sheet does not abort the whole run.

    Args:
        sheet_configs: list of dictionaries shaped like
            {"name": str, "header_row": int}, one per sheet to extract.

    Returns:
        dict: run summary shaped like
            {"successful": list[str], "failed": list[str], "total": int}.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    successful: list[str] = []
    failed: list[str] = []

    for config in sheet_configs:
        sheet_name = config["name"]
        header_row = config["header_row"]

        try:
            dataframe = extract_sheet(sheet_name, header_row)

            file_name = f"{_normalize_sheet_name(sheet_name)}.parquet"
            output_path = DATA_DIR / file_name
            dataframe.to_parquet(output_path, index=False)

            logger.info(
                "Sheet '%s' saved to '%s' (%d rows)",
                sheet_name,
                output_path,
                len(dataframe),
            )
            successful.append(sheet_name)

        except Exception as exc:
            logger.error(
                "Failed to extract sheet '%s': %s: %s",
                sheet_name,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            failed.append(sheet_name)
            continue

    summary = {
        "successful": successful,
        "failed": failed,
        "total": len(sheet_configs),
    }

    logger.info(
        "Run summary: %d successful %s, %d failed %s, %d sheets in total",
        len(successful),
        successful,
        len(failed),
        failed,
        summary["total"],
    )

    return summary


# ---------------------------------------------------------------------------
# Executable entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Configuration of the sheets to extract: exact name as it appears in
    # the spreadsheet and the row (1-indexed) where the header is located.
    # Edit header_row here if the structure of a sheet changes.
    SHEET_CONFIGS = [
        {"name": "Tatuajes", "header_row": 6},
        {"name": "Arte", "header_row": 6},
        {"name": "Maquillaje", "header_row": 6},
        {"name": "💸 Gastos", "header_row": 8},
        {"name": "💸 Retiros", "header_row": 8},
    ]

    extract_all_sheets(SHEET_CONFIGS)
