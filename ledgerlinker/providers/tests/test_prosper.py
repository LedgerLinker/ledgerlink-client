from unittest import TestCase
from unittest.mock import Mock, patch
from datetime import date
from ..base import ProviderException
from ..prosper import ProsperProvider


class ProsperTestCase(TestCase):

    def setUp(self):
        config = {}
        self.prosper_client_mock = Mock()
        try:
            self.provider = ProsperProvider(
                config,
                prosper_client=self.prosper_client_mock)

        except ProviderException as error:
            self.skipTest('Prosper provider missing dependency prosper. Skip Tests.')

    def test_fetch_purchases(self):
        self.prosper_client_mock.notes.return_value = EX1_NOTES
        results = self.provider.fetch_purchases(
            start_date=date(2020, 1, 1),
        )

        self.prosper_client_mock.notes.assert_called_once_with()

EX1_NOTES = [
    {
        'origination_date': '2020-01-01',
        'borrower_rate': 0.1,
        'loan_note_id': '4555-123',
        'amount_borrowed': 1000,
        'term': 36,
        'note_ownership_amount': 25,
        'prosper_rating': 'B'
    }, {
        'origination_date': '2020-05-01',
        'borrower_rate': 0.2,
        'loan_note_id': '4665-133',
        'amount_borrowed': 5000,
        'term': 42,
        'note_ownership_amount': 30,
        'prosper_rating': 'A'
    },
]
