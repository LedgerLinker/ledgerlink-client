from unittest import TestCase
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory
from datetime import date
from ..base import Provider, ProviderException


class ProviderBaseTestCase(TestCase):

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        config = Mock()
        config.output_dir = self.temp_dir.name

        self.provider = Provider(config)


    def test_register_output_and_store_row(self):
        """Register an output and open a csv file for append."""
        expected_file_path = self.temp_dir.name + '/test.csv'

        self.provider.get_fieldnames = Mock(
            return_value=['a', 'b', 'c'])

        self.provider.register_output('test', 'test.csv')

        self.provider.store_row('test', {
            'a': 1, 'b': 2, 'c': 3
        })

        self.provider.close()

        with open(expected_file_path, 'r') as output_file:
            lines = output_file.readlines()

        self.assertEqual(lines, [
            'a,b,c\n',
            '1,2,3\n',
        ])

    def test_store_no_output(self):
        """Test that we raise an error if output name not defined."""
        with self.assertRaises(ProviderException) as error:
            self.provider.store_row('test', {})

        self.assertEqual(str(error.exception), 'No outputs registered.')

    def test_store_no_output_one_registered(self):
        """Test that we raise an error if output name not defined."""
        self.provider.register_output('test', 'test.csv', ['a', 'b', 'c'])

        with self.assertRaises(ProviderException) as error:
            self.provider.store_row('booop', {})

        self.assertEqual(str(error.exception), 'Output booop not registered.')
