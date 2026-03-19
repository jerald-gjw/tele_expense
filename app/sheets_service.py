from __future__ import annotations

import logging
from datetime import date
from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

from app.config import Settings
from app.models import ExpenseEntry

LOGGER = logging.getLogger(__name__)
SHEET_HEADERS = ["Date", "Time", "Type", "Name", "Price"]
ANALYSIS_SHEET_NAME = "Analysis"
SUBSCRIPTIONS_SHEET_NAME = "Subscriptions"
SUBSCRIPTIONS_HEADERS = ["ChatId", "Enabled", "UpdatedAt"]


class SheetsService:
    def __init__(self, settings: Settings) -> None:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(
            settings.parsed_service_account_info,
            scopes=scopes,
        )
        self.client = gspread.authorize(credentials)
        spreadsheet = self.client.open_by_key(settings.google_sheet_id)
        self.spreadsheet = spreadsheet
        try:
            self.worksheet = spreadsheet.worksheet(settings.worksheet_name)
        except WorksheetNotFound:
            LOGGER.info("Worksheet '%s' not found. Creating it.", settings.worksheet_name)
            self.worksheet = spreadsheet.add_worksheet(title=settings.worksheet_name, rows=1000, cols=5)
        self._ensure_header()
        self._apply_visual_formatting()
        self._ensure_analysis_sheet()
        self._ensure_subscriptions_sheet()

    def _ensure_header(self) -> None:
        current_headers = self.worksheet.row_values(1)
        if current_headers != SHEET_HEADERS:
            self.worksheet.update("A1:E1", [SHEET_HEADERS])

    def _apply_visual_formatting(self) -> None:
        sheet_id = self.worksheet.id
        requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {
                            "frozenRowCount": 1,
                        },
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.13,
                                "green": 0.35,
                                "blue": 0.66,
                            },
                            "horizontalAlignment": "CENTER",
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1,
                                    "green": 1,
                                    "blue": 1,
                                },
                                "fontSize": 11,
                                "bold": True,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "LEFT",
                            "textFormat": {
                                "fontSize": 10,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(horizontalAlignment,textFormat.fontSize)",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "RIGHT",
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0.00",
                            },
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat,horizontalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "DATE",
                                "pattern": "yyyy-mm-dd",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "TIME",
                                "pattern": "hh:mm:ss",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 1,
                    },
                    "properties": {
                        "pixelSize": 120,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 1,
                        "endIndex": 2,
                    },
                    "properties": {
                        "pixelSize": 100,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 2,
                        "endIndex": 3,
                    },
                    "properties": {
                        "pixelSize": 130,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 3,
                        "endIndex": 4,
                    },
                    "properties": {
                        "pixelSize": 220,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 4,
                        "endIndex": 5,
                    },
                    "properties": {
                        "pixelSize": 110,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "addBanding": {
                    "bandedRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                            "endColumnIndex": 5,
                        },
                        "rowProperties": {
                            "firstBandColor": {
                                "red": 0.97,
                                "green": 0.98,
                                "blue": 1,
                            },
                            "secondBandColor": {
                                "red": 0.92,
                                "green": 0.95,
                                "blue": 1,
                            },
                            "headerColor": {
                                "red": 0.13,
                                "green": 0.35,
                                "blue": 0.66,
                            },
                        },
                    }
                }
            },
        ]

        try:
            self.worksheet.spreadsheet.batch_update({"requests": requests})
        except gspread.exceptions.APIError:
            LOGGER.info("Banding already exists or formatting partially applied; skipping duplicate format operations")

    def _ensure_analysis_sheet(self) -> None:
        try:
            analysis = self.spreadsheet.worksheet(ANALYSIS_SHEET_NAME)
        except WorksheetNotFound:
            LOGGER.info("Worksheet '%s' not found. Creating it.", ANALYSIS_SHEET_NAME)
            analysis = self.spreadsheet.add_worksheet(title=ANALYSIS_SHEET_NAME, rows=200, cols=8)

        title = analysis.acell("A1").value
        if title != "Expense Analysis Dashboard":
            self._initialize_analysis_sheet(analysis)

        self._repair_analysis_formulas(analysis)
        self._apply_analysis_dropdowns(analysis)
        self._apply_analysis_formatting(analysis)

    def _repair_analysis_formulas(self, analysis: gspread.Worksheet) -> None:
        analysis.update(
            "A16:B17",
            [
                ["Monthly Breakdown by Type", ""],
                ["Type", "Total"],
            ],
            value_input_option="USER_ENTERED",
        )
        analysis.update(
            "A18",
            [[
                "=IFERROR(QUERY(FILTER({Expenses!C2:C,Expenses!E2:E},LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,B5,1),\"yyyy-mm\")),\"select Col1,sum(Col2) group by Col1 order by sum(Col2) desc limit 10 label sum(Col2) ''\",0),\"\")",
            ]],
            value_input_option="USER_ENTERED",
        )
        analysis.update(
            "A30:B43",
            [
                ["Monthly Totals in Selected Year", ""],
                ["Month", "Total"],
                ["Jan", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,1,1),\"yyyy-mm\"))),0)"],
                ["Feb", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,2,1),\"yyyy-mm\"))),0)"],
                ["Mar", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,3,1),\"yyyy-mm\"))),0)"],
                ["Apr", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,4,1),\"yyyy-mm\"))),0)"],
                ["May", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,5,1),\"yyyy-mm\"))),0)"],
                ["Jun", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,6,1),\"yyyy-mm\"))),0)"],
                ["Jul", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,7,1),\"yyyy-mm\"))),0)"],
                ["Aug", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,8,1),\"yyyy-mm\"))),0)"],
                ["Sep", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,9,1),\"yyyy-mm\"))),0)"],
                ["Oct", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,10,1),\"yyyy-mm\"))),0)"],
                ["Nov", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,11,1),\"yyyy-mm\"))),0)"],
                ["Dec", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,12,1),\"yyyy-mm\"))),0)"],
            ],
            value_input_option="USER_ENTERED",
        )
        analysis.update(
            "A45:E47",
            [
                ["Recent 10 Expenses", "", "", "", ""],
                ["Date", "Time", "Type", "Name", "Price"],
                ["=IFERROR(QUERY(Expenses!A2:E,\"select A,B,C,D,E order by A desc, B desc limit 10\",0),\"\")", "", "", "", ""],
            ],
            value_input_option="USER_ENTERED",
        )

    def _apply_analysis_dropdowns(self, analysis: gspread.Worksheet) -> None:
        analysis.update(
            "G1:H2",
            [
                ["Helper_Date_List", "Helper_Year_List"],
                [
                    "=SORT(UNIQUE(FILTER(Expenses!A2:A,Expenses!A2:A<>\"\")),1,FALSE)",
                    "=SORT(UNIQUE(ARRAYFORMULA(YEAR(FILTER(Expenses!A2:A,Expenses!A2:A<>\"\")))),1,FALSE)",
                ],
            ],
            value_input_option="USER_ENTERED",
        )

        requests = [
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": analysis.id,
                        "startRowIndex": 3,
                        "endRowIndex": 4,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [{"userEnteredValue": "=Analysis!G2:G"}],
                        },
                        "strict": False,
                        "showCustomUi": True,
                    },
                }
            },
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": analysis.id,
                        "startRowIndex": 4,
                        "endRowIndex": 5,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [
                                {"userEnteredValue": "1"},
                                {"userEnteredValue": "2"},
                                {"userEnteredValue": "3"},
                                {"userEnteredValue": "4"},
                                {"userEnteredValue": "5"},
                                {"userEnteredValue": "6"},
                                {"userEnteredValue": "7"},
                                {"userEnteredValue": "8"},
                                {"userEnteredValue": "9"},
                                {"userEnteredValue": "10"},
                                {"userEnteredValue": "11"},
                                {"userEnteredValue": "12"},
                            ],
                        },
                        "strict": False,
                        "showCustomUi": True,
                    },
                }
            },
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": analysis.id,
                        "startRowIndex": 5,
                        "endRowIndex": 6,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [{"userEnteredValue": "=Analysis!H2:H"}],
                        },
                        "strict": False,
                        "showCustomUi": True,
                    },
                }
            },
        ]

        analysis.spreadsheet.batch_update({"requests": requests})

    def _ensure_subscriptions_sheet(self) -> None:
        try:
            subscriptions = self.spreadsheet.worksheet(SUBSCRIPTIONS_SHEET_NAME)
        except WorksheetNotFound:
            LOGGER.info("Worksheet '%s' not found. Creating it.", SUBSCRIPTIONS_SHEET_NAME)
            subscriptions = self.spreadsheet.add_worksheet(title=SUBSCRIPTIONS_SHEET_NAME, rows=200, cols=3)

        self.subscriptions_worksheet = subscriptions
        current_headers = subscriptions.row_values(1)
        if current_headers != SUBSCRIPTIONS_HEADERS:
            subscriptions.update("A1:C1", [SUBSCRIPTIONS_HEADERS])

    def _initialize_analysis_sheet(self, analysis: gspread.Worksheet) -> None:
        dashboard_rows = [
            ["Expense Analysis Dashboard", ""],
            ["", ""],
            ["Configuration", ""],
            ["Selected Date (dd/mm/yyyy)", "=TODAY()"],
            ["Selected Month (1-12)", "=MONTH(TODAY())"],
            ["Selected Year (yyyy)", "=YEAR(TODAY())"],
            ["Type Filter (optional)", ""],
            ["", ""],
            ["Core Metrics", ""],
            [
                "Total on Selected Date",
                "=IFERROR(SUM(FILTER(Expenses!E2:E, Expenses!A2:A=TEXT(B4,\"yyyy-mm-dd\"))),0)",
            ],
            [
                "Total in Selected Month",
                "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,B5,1),\"yyyy-mm\"))),0)",
            ],
            [
                "Total in Selected Year",
                "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,4)=TEXT(B6,\"0\"))),0)",
            ],
            [
                "Total on Selected Date + Type Filter",
                "=IF(B7=\"\",B10,IFERROR(SUM(FILTER(Expenses!E2:E, Expenses!A2:A=TEXT(B4,\"yyyy-mm-dd\"), LOWER(Expenses!C2:C)=LOWER(B7))),0))",
            ],
            [
                "Average Daily Spend (Selected Month)",
                "=IFERROR(B11/DAY(EOMONTH(DATE(B6,B5,1),0)),0)",
            ],
            ["", ""],
            ["Monthly Breakdown by Type", ""],
            ["Type", "Total"],
            [
                "=IFERROR(QUERY(FILTER({Expenses!C2:C,Expenses!E2:E},LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,B5,1),\"yyyy-mm\")),\"select Col1,sum(Col2) group by Col1 order by sum(Col2) desc limit 10 label sum(Col2) ''\",0),\"\")",
                "",
            ],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["", ""],
            ["Monthly Totals in Selected Year", ""],
            ["Month", "Total"],
            ["Jan", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,1,1),\"yyyy-mm\"))),0)"],
            ["Feb", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,2,1),\"yyyy-mm\"))),0)"],
            ["Mar", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,3,1),\"yyyy-mm\"))),0)"],
            ["Apr", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,4,1),\"yyyy-mm\"))),0)"],
            ["May", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,5,1),\"yyyy-mm\"))),0)"],
            ["Jun", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,6,1),\"yyyy-mm\"))),0)"],
            ["Jul", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,7,1),\"yyyy-mm\"))),0)"],
            ["Aug", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,8,1),\"yyyy-mm\"))),0)"],
            ["Sep", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,9,1),\"yyyy-mm\"))),0)"],
            ["Oct", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,10,1),\"yyyy-mm\"))),0)"],
            ["Nov", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,11,1),\"yyyy-mm\"))),0)"],
            ["Dec", "=IFERROR(SUM(FILTER(Expenses!E2:E, LEFT(Expenses!A2:A,7)=TEXT(DATE(B6,12,1),\"yyyy-mm\"))),0)"],
            ["", ""],
            ["Recent 10 Expenses", ""],
            ["Date", "Time", "Type", "Name", "Price"],
            ["=IFERROR(QUERY(Expenses!A2:E,\"select A,B,C,D,E order by A desc, B desc limit 10\",0),\"\")", "", "", "", ""],
        ]

        while len(dashboard_rows) < 60:
            dashboard_rows.append([""])

        normalized_rows = []
        for row in dashboard_rows[:60]:
            normalized_rows.append((row + ["", "", "", "", ""])[:5])

        analysis.update("A1:E60", normalized_rows, value_input_option="USER_ENTERED")

    def _apply_analysis_formatting(self, analysis: gspread.Worksheet) -> None:
        sheet_id = analysis.id
        requests = [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 1,
                    },
                    "properties": {
                        "pixelSize": 310,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 6,
                        "endIndex": 8,
                    },
                    "properties": {
                        "hiddenByUser": True,
                    },
                    "fields": "hiddenByUser",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 1,
                        "endIndex": 2,
                    },
                    "properties": {
                        "pixelSize": 220,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 2,
                        "endIndex": 5,
                    },
                    "properties": {
                        "pixelSize": 140,
                    },
                    "fields": "pixelSize",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.12,
                                "green": 0.33,
                                "blue": 0.62,
                            },
                            "horizontalAlignment": "LEFT",
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1,
                                    "green": 1,
                                    "blue": 1,
                                },
                                "fontSize": 14,
                                "bold": True,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": 60,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat.bold",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 3,
                        "endRowIndex": 4,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "DATE",
                                "pattern": "dd/mm/yyyy",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 9,
                        "endRowIndex": 47,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "RIGHT",
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0.00",
                            },
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat,horizontalAlignment)",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 45,
                        "endRowIndex": 46,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.13,
                                "green": 0.35,
                                "blue": 0.66,
                            },
                            "horizontalAlignment": "CENTER",
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1,
                                    "green": 1,
                                    "blue": 1,
                                },
                                "bold": True,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            },
            {
                "addBanding": {
                    "bandedRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 16,
                            "endRowIndex": 47,
                            "startColumnIndex": 0,
                            "endColumnIndex": 2,
                        },
                        "rowProperties": {
                            "firstBandColor": {
                                "red": 0.98,
                                "green": 0.99,
                                "blue": 1,
                            },
                            "secondBandColor": {
                                "red": 0.95,
                                "green": 0.97,
                                "blue": 1,
                            },
                        },
                    }
                }
            },
        ]

        try:
            analysis.spreadsheet.batch_update({"requests": requests})
        except gspread.exceptions.APIError:
            LOGGER.info("Analysis sheet formatting already exists or partially applied; skipping duplicate format operations")

    def append_expense(self, expense: ExpenseEntry) -> None:
        self.worksheet.append_row(expense.to_sheet_row(), value_input_option="USER_ENTERED")

    def subscribe_daily_summary(self, chat_id: int) -> None:
        chat_str = str(chat_id)
        values = self.subscriptions_worksheet.col_values(1)
        now_ts = date.today().isoformat()

        for idx, existing in enumerate(values[1:], start=2):
            if str(existing).strip() == chat_str:
                self.subscriptions_worksheet.update(
                    f"A{idx}:C{idx}",
                    [[chat_str, "TRUE", now_ts]],
                    value_input_option="USER_ENTERED",
                )
                return

        self.subscriptions_worksheet.append_row([chat_str, "TRUE", now_ts], value_input_option="USER_ENTERED")

    def unsubscribe_daily_summary(self, chat_id: int) -> None:
        chat_str = str(chat_id)
        values = self.subscriptions_worksheet.col_values(1)
        now_ts = date.today().isoformat()

        for idx, existing in enumerate(values[1:], start=2):
            if str(existing).strip() == chat_str:
                self.subscriptions_worksheet.update(
                    f"A{idx}:C{idx}",
                    [[chat_str, "FALSE", now_ts]],
                    value_input_option="USER_ENTERED",
                )
                return

        self.subscriptions_worksheet.append_row([chat_str, "FALSE", now_ts], value_input_option="USER_ENTERED")

    def get_daily_subscribers(self) -> list[int]:
        records = self.subscriptions_worksheet.get_all_records(expected_headers=SUBSCRIPTIONS_HEADERS)
        subscribers: list[int] = []
        for record in records:
            enabled = str(record.get("Enabled", "")).strip().lower() in {"true", "1", "yes"}
            if not enabled:
                continue
            try:
                subscribers.append(int(str(record.get("ChatId", "")).strip()))
            except ValueError:
                LOGGER.warning("Skipping invalid ChatId in subscriptions sheet: %s", record.get("ChatId"))
        return subscribers

    def get_today_total(self, for_day: date) -> float:
        target = for_day.strftime("%Y-%m-%d")
        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        total = 0.0
        for record in records:
            if str(record.get("Date", "")).strip() == target:
                total += self._safe_float(record.get("Price"))
        return round(total, 2)

    def get_month_total(self, for_day: date) -> float:
        target_prefix = for_day.strftime("%Y-%m")
        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        total = 0.0
        for record in records:
            if str(record.get("Date", "")).strip().startswith(target_prefix):
                total += self._safe_float(record.get("Price"))
        return round(total, 2)

    def get_daily_breakdown(self, for_day: date) -> tuple[float, list[tuple[str, float]]]:
        target = for_day.strftime("%Y-%m-%d")
        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        totals_by_type: dict[str, float] = defaultdict(float)
        total = 0.0

        for record in records:
            if str(record.get("Date", "")).strip() != target:
                continue

            price = self._safe_float(record.get("Price"))
            expense_type = str(record.get("Type", "")).strip().lower() or "other"
            totals_by_type[expense_type] += price
            total += price

        breakdown = sorted(totals_by_type.items(), key=lambda item: item[1], reverse=True)
        return round(total, 2), [(label, round(amount, 2)) for label, amount in breakdown]

    def get_monthly_breakdown(self, for_day: date) -> tuple[float, list[tuple[str, float]]]:
        target_prefix = for_day.strftime("%Y-%m")
        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        totals_by_type: dict[str, float] = defaultdict(float)
        total = 0.0

        for record in records:
            if not str(record.get("Date", "")).strip().startswith(target_prefix):
                continue

            price = self._safe_float(record.get("Price"))
            expense_type = str(record.get("Type", "")).strip().lower() or "other"
            totals_by_type[expense_type] += price
            total += price

        breakdown = sorted(totals_by_type.items(), key=lambda item: item[1], reverse=True)
        return round(total, 2), [(label, round(amount, 2)) for label, amount in breakdown]

    def get_weekly_breakdown(self, for_day: date) -> tuple[float, list[tuple[str, float]]]:
        week_start = for_day.fromordinal(for_day.toordinal() - for_day.weekday())
        week_end = week_start.fromordinal(week_start.toordinal() + 6)

        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        totals_by_type: dict[str, float] = defaultdict(float)
        total = 0.0

        for record in records:
            raw_date = str(record.get("Date", "")).strip()
            try:
                record_date = date.fromisoformat(raw_date)
            except ValueError:
                continue

            if record_date < week_start or record_date > week_end:
                continue

            price = self._safe_float(record.get("Price"))
            expense_type = str(record.get("Type", "")).strip().lower() or "other"
            totals_by_type[expense_type] += price
            total += price

        breakdown = sorted(totals_by_type.items(), key=lambda item: item[1], reverse=True)
        return round(total, 2), [(label, round(amount, 2)) for label, amount in breakdown]

    def get_daily_details(self, for_day: date) -> tuple[float, list[tuple[str, str, str, str, float]]]:
        target = for_day.strftime("%Y-%m-%d")
        records = self.worksheet.get_all_records(expected_headers=SHEET_HEADERS)
        details: list[tuple[str, str, str, str, float]] = []
        total = 0.0

        for record in records:
            record_date = str(record.get("Date", "")).strip()
            if record_date != target:
                continue

            record_time = str(record.get("Time", "")).strip()
            expense_type = str(record.get("Type", "")).strip().lower() or "other"
            name = str(record.get("Name", "")).strip()
            price = self._safe_float(record.get("Price"))
            details.append((record_date, record_time, expense_type, name, round(price, 2)))
            total += price

        details.sort(key=lambda row: row[1])
        return round(total, 2), details

    @staticmethod
    def _safe_float(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            LOGGER.warning("Skipping non-numeric price in sheet: %s", value)
            return 0.0
