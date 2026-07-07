"""
test_connection.py

Minimal manual check that authentication and access to the Google Sheets
spreadsheet configured via GOOGLE_CREDENTIALS_PATH and SPREADSHEET_ID work
correctly. Opens the spreadsheet and lists its worksheets.
"""

from sheets_extractor import _get_gspread_client, SPREADSHEET_ID


def test_connection() -> None:
    client = _get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    print(f"Connected to spreadsheet: '{spreadsheet.title}'")
    print("Worksheets found:")
    for worksheet in spreadsheet.worksheets():
        print(f"  - {worksheet.title!r} ({worksheet.row_count} rows, {worksheet.col_count} cols)")


if __name__ == "__main__":
    test_connection()
