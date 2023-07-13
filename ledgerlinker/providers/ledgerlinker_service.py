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
from .base import Provider, ProviderConfig
from ledgerlinker.update_tracker import LastUpdateTracker

DEFAULT_SERVICE_BASE_URL = 'https://app.ledgerlinker.com'

class LedgerLinkerException(Exception):
    pass


class LedgerLinkerServiceProvider(Provider):

    def __init__(self, config : ProviderConfig):
        super().__init__(config)

        if hasattr(config, 'service_base_url'):
            self.service_base_url = config.service_base_url
        else:
            self.service_base_url = DEFAULT_SERVICE_BASE_URL

        try:
            self.token = config.token
        except AttributeError:
            raise LedgerLinkerException('No ledgerlinker service token found in config file.')

        try:
            self._category_separator = config.category_separator
        except AttributeError:
            self._category_separator = ':'


    def get_headers(self) -> dict:
        return {'Authorization': f'Token {self.token}'}

    def get_available_exports(self):
        """Get a list of available exports from the LedgerLinker service."""
        url = f'{self.service_base_url}/api/exports/'
        response = requests.get(url, headers=self.get_headers())

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
        if len(payload['transactions']) > 0:
            cleaned_transactions = [
                self.format_transaction_data(transaction)
                for transaction in payload['transactions']
            ]

            latest_transaction_date = date.fromisoformat(payload['latest_transaction'])
        else:
            cleaned_transactions = []
            latest_transaction_date = start_date

        return (
            cleaned_transactions,
            payload['fieldnames'],
            latest_transaction_date
        )

    def format_transaction_data(self, transaction):
        """Format the transaction data to be written to the CSV file."""
        data = transaction.copy()
        if 'categories' in data:
            data['categories'] = self._category_separator.join(data['categories'])
        return data

    def filter_exports(self, exports, desired_exports):
        """Filter exports by the desired exports in the config file."""
        if desired_exports is None:
            return exports

        filtered_exports = []
        for export in exports:
            if export['slug'] in desired_exports:
                filtered_exports.append(export)

        return filtered_exports

    def get_fieldnames(self, output_name):
        raise NotImplemented('get_fieldnames not implemented for LedgerLinkerServiceProvider')

    def sync_export(self, export_details : dict, update_tracker : LastUpdateTracker):
        """Sync transactions for a single export from the LedgerLinker service."""
        print(f'Fetching export: {export_details["name"]}')

        export_name = f"{self.config.name}-{export_details['slug']}"
        start_date = None

        last_update_date = update_tracker.get(export_name)
        if last_update_date:
            start_date = last_update_date + timedelta(days=1)
            if start_date > date.today():
                print(f'Export {export_name} is already up to date.')
                return

        print(f'Fetching transactions since {start_date}.')
        new_transactions, fieldnames, latest_transaction_date = self.get_export(
            export_details['slug'],
            export_details['json_download_url'],
            start_date=start_date,
        )

        self.register_output(export_name, f"{export_details['slug']}.csv", fieldnames)
        self.store(export_name, new_transactions)

        update_tracker.update(export_name, latest_transaction_date)


    def sync(self, last_links : LastUpdateTracker):
        """Sync the latest transactions from the LedgerLinker service."""
        exports = self.get_available_exports()
        exports = self.filter_exports(exports, self.config.exports)

        for export_details in exports:
            self.sync_export(export_details, last_links)
