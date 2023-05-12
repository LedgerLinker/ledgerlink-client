from typing import Optional, List, Dict
import os
import sys
import argparse
import json
from json import JSONDecodeError
from datetime import date
import commentjson
from ledgerlinker.providers import get_providers
from ledgerlinker.providers.base import Provider, ProviderConfig

DEFAULT_CONFIG_FILE = '~/.ledgerlink-config.json'

class LedgerLinkerException(Exception):
    pass

class ClientConfig:
    def __init__(self, global_config, providers):
        self.providers = providers
        self.config = global_config

class LedgerLinkerClient:
    """A client for using LedgerLinker Providers."""

    def _load_config_file(self, config_file_path : str):
        """Load the config file from the given path."""
        try:
            with open(config_file_path, 'r') as config_file:
                config = commentjson.load(config_file)
        except FileNotFoundError:
            print(f'Config file not found at {config_file_path}. Please run `ledgerlinker config` to generate a config file.')
            sys.exit(1)

        if 'providers' not in config:
            print('No providers found in config file.')
            sys.exit(1)

        if type(config['providers']) is not list:
            print('Providers must be a list.')
            sys.exit(1)

        if 'output_dir' not in config:
            print('No output_dir found in config file.')
            sys.exit(1)

        self.output_dir = config['output_dir']

        providers = {}
        for provider_config in config['providers']:
            if 'name' not in provider_config:
                print('No name found in provider config. Please run `ledgerlinker config` to generate a config file.')
                sys.exit(1)

            provider_name = provider_config['name']
            if provider_name in providers:
                print(f'Provider with name {provider_name} already exists.')
                sys.exit(1)

            if 'output_dir' not in provider_config:
                provider_config['output_dir'] = self.output_dir

            config = ProviderConfig(**provider_config)
            providers[provider_config['name']] = config

        self._last_link_path = f'{self.output_dir}/.last_links.json'
        return ClientConfig(config, providers)

    def get_last_link_path(self):
        return self._last_link_path

    def store_last_link_file(self, latest_transaction_by_export_id : dict):
        """Store the last link file which contains the last time each export was synced."""
        with open(self.get_last_link_path(), 'w') as config_file:

            config_file.write(json.dumps({
                export_id: latest_transaction.isoformat()
                for export_id, latest_transaction in latest_transaction_by_export_id.items()
            }))

    def load_last_link_file(self) -> Dict[str, date]:
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

    def __init__(self, config_file_path):
        self.config = self._load_config_file(config_file_path)

        self.last_links = self.load_last_link_file()
        self.providers = get_providers(self.config.providers)

    def sync(self):
        for provider_name, provider in self.providers.items():
            print(f'Running sync for {provider_name}...')
            provider.sync(self.last_links)


def main():
    parser = argparse.ArgumentParser(description='Sync client for the LedgerLinker Service.')
    parser.add_argument('-c', '--config', required=True, help='Path to LedgerLinker Sync config file')

    args = parser.parse_args()

    client = LedgerLinkerClient(args.config)
    client.sync()

if __name__ == '__main__':
    main()
