import os
import sys
import argparse
import requests
import json
import commentjson
from pathlib import Path
from json import JSONDecodeError
from csv import DictWriter
from datetime import datetime, date, timedelta


DEFAULT_SERVICE_BASE_URL = 'https://app.ledgerlinker.com'
DEFAULT_CONFIG_FILE = '~/.ledgerlink-config.json'

class LedgerLinkerException(Exception):
    pass

class LedgerLinkerClient:
    """A client for retrieving transaction data from the LedgerLinker API."""

    def __init__(self, config_file_path=None):
        if config_file_path is None:
            config_file_path = DEFAULT_CONFIG_FILE

        self.config = self.load_config_file(config_file_path)

        if 'token' not in self.config:
            print('No token found in config file. Please run `ledgerlinker config` to generate a token.')
            sys.exit(1)

        if 'link_dir' not in self.config:
            print('No link_dir found in config file. Please run `ledgerlinker config` to generate a link_dir.')
            sys.exit(1)

        # This is really only helpful for testing purposes.
        self.service_base_url = self.config.get(
            'service_url',
            DEFAULT_SERVICE_BASE_URL)

        self.token = self.config['token']
        self.link_dir = self.config['link_dir']

        # Check if link dir exists. If not create it.
        if not os.path.exists(self.link_dir):
            print(f'Note: Link directory "{self.link_dir}" does not exist. Creating it now!')
            os.makedirs(self.link_dir, exist_ok=True)

        self.desired_exports = self.config.get('exports', None)

        self.should_append_transactions = self.config.get('append_transactions', True)

    def load_config_file(self, config_file_path : str):
        """Load the config file from the given path."""
        try:
            with open(config_file_path, 'r') as config_file:
                config = commentjson.load(config_file)
        except FileNotFoundError:
            print(f'Config file not found at {config_file_path}. Please run `ledgerlinker config` to generate a config file.')
            sys.exit(1)
        return config

    def get_headers(self):
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

    def get_export_file_path(self, nickname, append_mode):
        fetch_time = datetime.today().strftime("%m-%d-%Y_%H-%M")
        if append_mode:
            return f'{self.link_dir}/{nickname}.csv'
        else:
            return f'{self.link_dir}/{nickname}-{fetch_time}.csv'

    def get_export(self, nickname, json_url : str, start_date=None, append_mode=False):
        params = {}
        if start_date is not None:
            params['start_date'] = start_date

        response = requests.get(json_url, headers=self.get_headers(), params=params)
        if response.status_code != 200:
            raise LedgerLinkerException('Error retrieving export from LedgerLinker service.')

        file_path = self.get_export_file_path(nickname, append_mode)

        payload = response.json()

        if len(payload['transactions']) == 0:
            return None

        if append_mode:
            self.append_transactions(file_path, payload['fieldnames'], payload['transactions'])
        else:
            self.store_transactions(file_path, payload['fieldnames'], payload['transactions'])

        return date.fromisoformat(payload['latest_transaction'])

    def store_transactions(self, file_path, field_names, transactions):
        with open(file_path, 'w') as f:
            writer = DictWriter(f, fieldnames=field_names)
            writer.writeheader()
            for transaction in transactions:
                writer.writerow(transaction)

    def append_transactions(self, file_path, field_names, transactions):
        exists = False
        if Path(file_path).is_file():
            exists = True

        with open(file_path, 'a') as f:
            writer = DictWriter(f, fieldnames=field_names)

            if not exists:
                writer.writeheader()

            for transaction in transactions:
                writer.writerow(transaction)



    def get_last_link_path(self):
        return f'{self.link_dir}/.last_links.json'

    def store_last_link_file(self, latest_transaction_by_export_id : dict):
        """Store the last link file which contains the last time each export was synced."""
        with open(self.get_last_link_path(), 'w') as config_file:

            config_file.write(json.dumps({
                export_id: latest_transaction.isoformat()
                for export_id, latest_transaction in latest_transaction_by_export_id.items()
            }))

    def load_last_link_file(self):
        """Load lastlink file which contains the last time each export was synced."""
        try:
            with open(self.get_last_link_path(), 'r') as last_links_fp:
                last_links = json.load(last_links_fp)
        except FileNotFoundError:
            return {}
        except JSONDecodeError:
            print('The last link file is corrupt. Please delete it and try again.')
            sys.exit(1)

        last_links_by_export_slug = {}
        for link_slug, last_link in last_links.items():
            try:
                last_links_by_export_slug[link_slug] = date.fromisoformat(last_link)
            except ValueError:
                print('The last link file is corrupt. Please delete it and try again.')
                sys.exit(1)

        return last_links_by_export_slug

    def filter_exports(self, exports, desired_exports):
        """Filter exports by the desired exports in the config file."""
        if desired_exports is None:
            return exports

        filtered_exports = []
        for export in exports:
            if export['slug'] in desired_exports:
                filtered_exports.append(export)

        return filtered_exports

    def sync(self):
        """Sync the latest transactions from the LedgerLinker service."""
        exports = self.get_available_exports()
        exports = self.filter_exports(exports, self.desired_exports)

        last_update_details = self.load_last_link_file()

        for export in exports:
            export_slug = export['slug']
            print(f'Fetching export: {export["name"]}')

            start_date = None
            if export_slug in last_update_details:
                start_date = last_update_details[export_slug] + timedelta(days=1)
                print(start_date)

            new_transaction_date = self.get_export(
                export['slug'],
                export['json_download_url'],
                start_date=start_date,
                append_mode=self.should_append_transactions
            )

            if new_transaction_date is not None:
                last_update_details[export_slug] = new_transaction_date

        print(last_update_details)
        self.store_last_link_file(last_update_details)

def main():
    parser = argparse.ArgumentParser(description='Sync client for the LedgerLinker Service.')
    parser.add_argument('-c', '--config', required=True, help='Path to LedgerLinker Sync config file')

    args = parser.parse_args()

    client = LedgerLinkerClient(args.config)
    client.sync()

if __name__ == '__main__':
    main()
