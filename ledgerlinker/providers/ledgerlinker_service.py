"""This module provides a "provider" class that can be used to access the LedgerLinker Service.

The Ledgerlinker service allows access to accounts at Banks and other financial institutions using
a paid account aggregation service.
"""
from typing import Dict, Optional, Tuple, List
import requests
import sys
from csv import DictWriter
from pathlib import Path
from datetime import datetime, date, timedelta
from .base import Provider

DEFAULT_SERVICE_BASE_URL = 'https://app.ledgerlinker.com'

class LedgerLinkerException(Exception):
    pass


class LedgerLinkerServiceProvider(Provider):

    def get_headers(self) -> dict:
        return {'Authorization': f'Token {self.token}'}

    def get_available_exports(self):
        """Get a list of available exports from the LedgerLinker service."""
        url = f'{self.service_base_url}/api/exports/'
        response = requests.get(url, headers=self.get_headers())
        print(url)
        if response.status_code == 401:
            print('Error retrieving exports from LedgerLinker service. Your token appears to be invalid.')
            sys.exit(1)

        if response.status_code != 200:
            print('Error retrieving exports from LedgerLinker service.')
            sys.exit(1)

        return response.json()

    def get_export_file_path(self, nickname : str, append_mode : bool):
        fetch_time = datetime.today().strftime("%m-%d-%Y_%H-%M")
        if append_mode:
            return f'{self.link_dir}/{nickname}.csv'
        else:
            return f'{self.link_dir}/{nickname}-{fetch_time}.csv'

    def get_export(self, nickname : str, json_url : str, start_date = None) -> Tuple[List[Dict], str, date]:
        params = {}
        if start_date is not None:
            params['start_date'] = start_date

        response = requests.get(json_url, headers=self.get_headers(), params=params)
        if response.status_code != 200:
            raise LedgerLinkerException('Error retrieving export from LedgerLinker service.')

        payload = response.json()
        if len(payload['transactions']) == 0:
            return None

        cleaned_transactions = [
            self.format_transaction_data(transaction)
            for transaction in payload['transactions']
        ]

        latest_transaction = date.fromisoformat(payload['latest_transaction'])
        return (
            cleaned_transactions,
            payload['fieldnames'],
            latest_transaction
        )

    def format_transaction_data(self, transaction):
        """Format the transaction data to be written to the CSV file."""
        data = transaction.copy()
        if 'categories' in data:
            data['categories'] = ','.join(data['categories'])
        return data

    def store_transactions(self, file_path, fieldnames, transactions):
        exists = False
        if Path(file_path).is_file():
            exists = True

        with open(file_path, 'a+') as fp:
            writer = DictWriter(fp, fieldnames=fieldnames, lineterminator='\n')

            if not exists:
                writer.writeheader()

            for transaction in transactions:
                cleaned_transaction = self.format_transaction_data(transaction)
                writer.writerow(cleaned_transaction)

    def sync(self, last_update_dates : Optional[Dict[str, date]] = None):
        """Sync the latest transactions from the LedgerLinker service."""
        exports = self.get_available_exports()
        exports = self.filter_exports(exports, self.desired_exports)

        for export in exports:
            export_slug = export['slug']
            print(f'Fetching export: {export["name"]}')

            start_date = None
            if export_slug in last_update_dates:
                start_date = last_update_dates[export_slug] + timedelta(days=1)
                print(start_date)

            new_transactions, latest_transaction_date, fieldnames = self.get_export(
                export['slug'],
                export['json_download_url'],
                start_date=start_date,
            )

            append_mode = True
            file_path = self.get_export_file_path(export_slug, append_mode)

            self.store_transactions(file_path, fieldnames, new_transactions)

            if latest_transaction_date is not None:
                last_update_dates[export_slug] = latest_transaction_date

        print(last_update_dates)

        # TODO STORE LAST UPDATE DATES
        #self.store_last_link_file(last_update_details)
