"""This module provides a "provider" class that can be used to access the Google Sheets Service.
"""
from typing import Dict, Optional, Tuple, List
import requests
import sys
from csv import DictWriter
from pathlib import Path
from datetime import datetime, date, timedelta
from .base import Provider, ProviderConfig
from ledgerlinker.update_tracker import LastUpdateTracker

try:
    import gspread
    from gspread.client import Client
    from google_auth_oauthlib.flow import Flow
except ImportError:
    print('Google Sheet Provider: google_auth_oauthlib and gspread packages are required.')
    sys.exit(1)



class GoogleSheetProviderException(Exception):
    pass


class GoogleSheetsProvider(Provider):

    def __init__(self, config : ProviderConfig):
        super().__init__(config)

        if hasattr(config, 'google_secrets_file_path'):
            self.google_secrets_file_path = config.google_secrets_file_path

    def login(self):
        # Set up credentials
        google_scopes = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        flow = Flow.from_client_secrets_file(
            self.google_secrets_file_path,
            scopes=google_scopes,
            redirect_uri='http://localhost:8080/oauth')

        # Tell the user to go to the authorization URL.
        auth_url, _ = flow.authorization_url(prompt='consent')

        print('Please go to this URL: {}'.format(auth_url))

        # ENTER CODE HERE
        code = ''
        flow.fetch_token(code=code)

        # Store credentials so we can access them again

    def get_google_auth_flow(self) -> Flow:
        return None

    def get_spreadsheet_data(
            self,
            spreadsheet_id : str,
            worksheet_id : str
    ):
        flow = self.get_google_auth_flow()
        gc = Client(flow.credentials)

        sheet = gc.open_by_key(spreadsheet_id)
        worksheet = sheet.get_worksheet_by_id(worksheet_id)

        rows = worksheet.get_all_records(head=1, empty2zero=False)

        for row in rows:
            row_data = {
                header: row[header]
                for header in desired_headers
            }

            try:
                row_data[date_field] = datetime.strptime(
                    row_data[date_field],
                    date_format_str).date()
            except ValueError:
                print(f"Invalid date format for row {row_data}.. Skipping.")
                continue

            yield row_data


    def sync(self, last_links : LastUpdateTracker):
        """Sync the latest transactions from the LedgerLinker service."""

        export_name = f"gsheet-{self.config.name}"
        start_date = None

        last_update_date = last_links.get(export_name)
        if last_update_date:
            start_date = last_update_date + timedelta(days=1)
            if start_date > date.today():
                print(f'Export {export_name} is already up to date.')
                return

        print(f'Fetching transactions since {start_date}.')
        row_data, latest_transaction_date = self.get_spreadsheet_data(
            spreadsheet_id=self.spreadsheet_id,
            worksheet_id=self.worksheet_id,
            start_date=start_date,
        )

        self.register_output(export_name, f"{export_details['slug']}.csv", fieldnames)
        self.store(export_name, new_transactions)

        last_links.update(export_name, latest_transaction_date)
