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
