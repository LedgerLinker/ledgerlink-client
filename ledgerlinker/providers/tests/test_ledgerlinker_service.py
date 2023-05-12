from unittest import TestCase
from unittest.mock import Mock, patch
from datetime import date
from ..base import ProviderException
from ..ledgerlinker_service import LedgerLinkerServiceProvider


class LedgerLinkerProviderTestCase(TestCase):

    def setUp(self):
        config = {}
        self.prosper_client_mock = Mock()
        self.provider = LedgerLinkerServiceProvider(config)


    def test_get_available_exports(self):
        self.assertEqual(
            self.provider.get_available_exports(),
            ['check', 'sav', 'party']
        )
