from unittest import TestCase, skip
from unittest.mock import Mock, patch
from datetime import date
from ledgerlinker.providers.base import ProviderException, ProviderConfig
from ledgerlinker.providers.ledgerlinker_service import LedgerLinkerServiceProvider


class LedgerLinkerProviderTestCase(TestCase):

    def setUp(self):
        config = ProviderConfig(
            name='bank-test',
            token='123-token',
            output_dir='/tmp',
        )
        self.prosper_client_mock = Mock()
        self.ledgerlinker_provider = LedgerLinkerServiceProvider(config)


    @patch('ledgerlinker.providers.ledgerlinker_service.requests.get')
    def test_get_available_exports(self, mock_get):
        """Test getting available exports from LedgerLinker."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = EX1_AVAILABLE_EXPORT_RESPONSE
        self.assertEqual(
            self.ledgerlinker_provider.get_available_exports(),
            EX1_AVAILABLE_EXPORT_RESPONSE
        )

        mock_get.assert_called_once_with(
            'https://app.ledgerlinker.com/api/exports/',
            headers={'Authorization': 'Token 123-token'}
        )

    @patch('ledgerlinker.providers.ledgerlinker_service.requests.get')
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

        result = self.ledgerlinker_provider.get_export(
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

    def test_sync_export(self):
        """Test syncing a single export file."""

        new_transactions = ['TRANS']
        latest_transaction_date = date(2020, 1, 1)
        fieldnames = ['date', 'amount', 'description']

        update_tracker = Mock()
        update_tracker.get.return_value = date(2020, 1, 5)

        self.ledgerlinker_provider.register_output = Mock()
        self.ledgerlinker_provider.store = Mock()

        self.ledgerlinker_provider.get_export = Mock(return_value=(
            new_transactions, fieldnames, latest_transaction_date
        ))
        export_details = {
            'name': 'Test Export',
            'slug': 'test-export',
            'json_download_url': 'https://superledgerlink.test/api/v1/transaction_exports/1/download.json',
            'csv_download_url': 'https://superledgerlink.test/api/v1/transaction_exports/1/download.csv',
        }

        self.ledgerlinker_provider.sync_export(export_details, update_tracker)
        self.ledgerlinker_provider.register_output.assert_called_with('bank-test-test-export', 'test-export.csv', fieldnames)
        self.ledgerlinker_provider.store.assert_called_with('bank-test-test-export', ['TRANS'])

        self.ledgerlinker_provider.get_export.assert_called_once_with(
            'test-export',
            export_details['json_download_url'],
            start_date=date(2020, 1, 6))


EX1_AVAILABLE_EXPORT_RESPONSE = [
    {
        "slug": "bank-one-super-credit",
        "name": "Bank One Super Credit Card",
        "csv_download_url": "https://app.ledgerlinker.com/exports/bank-one-super-credit/download/csv/",
        "json_download_url": "https://app.ledgerlinker.com/exports/bank-one-super-credit/download/"
    },
    {
        "slug": "wealthy-ira-5555",
        "name": "Wealthy IRA 5555",
        "csv_download_url": "https://app.ledgerlinker.com/exports/wealthy-ira-5555/download/csv/",
        "json_download_url": "https://app.ledgerlinker.com/exports/wealthy-ira-5555/download/"
    }
]
