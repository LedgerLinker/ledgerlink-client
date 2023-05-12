from unittest import TestCase
from unittest.mock import patch
import json
from datetime import date
from tempfile import TemporaryDirectory

from ledgerlinker.client import LedgerLinkerClient


class LedgerLinkerClientTestCase(TestCase):

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.config = {
            'api_url': 'https://superledgerlink.test/api/v1',
            'token': '123-token',

            'link_dir': self.temp_dir.name,
        }

        config_file_path = self.temp_dir.name + '/config.json'
        with open(config_file_path, 'w') as config_file:
            config_file.write(json.dumps(self.config))

        self.client = LedgerLinkerClient(config_file_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_last_link_file(self):
        self.client.store_last_link_file({
            'check': date(2020, 1, 1),
            'sav': date(2020, 1, 12),
            'party': date(2020, 1, 1),
        })

        reload_last_links = self.client.load_last_link_file()

        self.assertEqual(reload_last_links['check'], date(2020,1,1))
        self.assertEqual(reload_last_links['sav'], date(2020,1,12))
        self.assertEqual(reload_last_links['party'], date(2020,1,1))

    @patch('ledgerlinker.client.requests.get')
    def test_get_export(self, mock_get):
        """Test getting a single export file and writing to disk."""

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'fieldnames': ['date', 'amount', 'description'],
            'transactions': [
                {'date': '2020-01-01', 'amount': 1.00, 'description': 'POOP'},
            ],
            'latest_transaction': '2020-01-01',
        }

        result = self.client.get_export(
            'testnick',
            'https://superledgerlink.test/api/v1/transaction_exports/1/download.json',
            date(2020,1,1)
        )

        mock_get.assert_called_with(
            'https://superledgerlink.test/api/v1/transaction_exports/1/download.json',
            headers={'Authorization': 'Token 123-token'},
            params={
                'start_date': date(2020, 1, 1)
            })
