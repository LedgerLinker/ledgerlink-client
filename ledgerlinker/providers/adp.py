"""Provider to download ADP pay statements."""
from typing import Optional
import json
import requests
import csv
from datetime import date, datetime
from .base import Provider, ProviderConfig
from ledgerlinker.update_tracker import LastUpdateTracker

class ADPProvider(Provider):

    def __init__(self, config : ProviderConfig):
        super().__init__(config)

        if hasattr(config, 'session_cookie'):
            session_cookie = config.session_cookie
        else:
            session_cookie = input('Please log into ADP and retrieve the session cookie:')

        self._statement_downloader = ADPStatementDownloader(session_cookie)

    def sync(self, update_tracker : LastUpdateTracker):
        """Sync the latest transactions from the LedgerLinker service."""

        export_name = f"{self.config.name}-adp-statements"
        last_update_date = update_tracker.get(export_name)

        statement_data = self._statement_downloader.download_statements(start_date=last_update_date)

        statements = list(statement_data.values())
        statements = sorted(statements, key=lambda statement: statement['payDate'])

        if hasattr(self.config, 'desired_fields'):
            desired_fields = self.config.desired_fields
        else:
            desired_fields = set()
            for statement in statement_data.values():
                desired_fields.update(statement.keys())

        self.register_output(export_name, f"{self.config.name}.csv", desired_fields)
        self.store(export_name, statements)

        # Save the date of the last paycheck as the most recent update date.
        last_update_date = statements[-1]['payDate']
        update_tracker.update(export_name, last_update_date)


class ADPStatementDownloader:
    """Download ADP pay statements."""

    STATEMENT_LIST_URL = 'https://my.adp.com/myadp_prefix/v1_0/O/A/payStatements?adjustments=yes&numberoflastpaydates=160'
    STATEMENT_DETAIL_BASE_URL = 'https://my.adp.com/myadp_prefix'

    def __init__(self, session_cookie):
        self.session_cookie = session_cookie

    def get(self, url):
        result = requests.get(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            },
            cookies={
                'SMSESSION': self.session_cookie
            }, allow_redirects=False
        )

        if result.status_code != 200:
            raise Exception('Request failed. Try updating your session cookie.')

        return result.json()

    def _get_statement_data_from_response(self, statement_data):
        """Build a simple dict of statement data from the response of statement detail endpoint."""
        data = {
            'payDate': statement_data['payDate'],
            'netPayAmount': statement_data['netPayAmount']['amountValue'],
            'grossPayAmount': statement_data['grossPayAmount']['amountValue'],
        }

        for deduction in statement_data['deductions']:
            try:
                name = deduction['CodeName'].strip()
                amount = deduction['deductionAmount']['amountValue']
            except KeyError:
                continue

            data[name] = amount

        return data

    def get_statement_detail(self, statement_detail_url):
        """Retrieve statement data using its detail url

        /v1_0/O/A/payStatement/0753543723172038101304001385327
        """
        result = self.get(self.STATEMENT_DETAIL_BASE_URL + statement_detail_url)
        statement_data = self._get_statement_data_from_response(result['payStatement'])
        statement_data['url'] = statement_detail_url
        return statement_data

    def get_available_statements(self, start_date : Optional[date] = None):
        """Retrieve a list of available statements from ADP."""
        result = self.get(self.STATEMENT_LIST_URL)
        statement_response = result['payStatements']

        for statement_data in statement_response:
            statement = statement_data.copy()
            statement['payDate'] = date.fromisoformat(statement_data['payDate'])

            # Ignore statements before the start date
            if start_date:
                if statement['payDate'] < start_date:
                    continue

            yield statement

    def load_cache_file(self, cache_file_path):
        try:
            with open(cache_file_path, 'r') as f:
                statements = {}
                for statement_key, statement_data in json.load(f).items():
                    statement_data['payDate'] = date.fromisoformat(statement_data['payDate'])
                    statements[statement_key] = statement_data
                return statements

        except FileNotFoundError:
            return {}

    def _json_serializer(self, obj):
        """JSON serializer for objects not serializable by default json code"""

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj

    def store_cache_file(self, cache_file_path, data):
        with open(cache_file_path, 'w') as f:
            json.dump(data, f, default=self._json_serializer)

    def download_statements(self, start_date : Optional[date] = None, flush_cache : bool = False):
        """Download all available statements from ADP after the start date."""
        if flush_cache:
            statement_data = {}
        else:
            statement_data = self.load_cache_file('adp_statement_cache.json')

        available_statements = self.get_available_statements(start_date)
        for statement_metadata in available_statements:
            detail_url = statement_metadata['payDetailUri']['href']
            if detail_url in statement_data:
                payDate = statement_data[detail_url]['payDate']
                print(f'Skipping {payDate}.. already downloaded.')
                continue

            print(f"Downloading statement {statement_metadata['payDate']}...")
            try:
                statement_data[detail_url] = self.get_statement_detail(detail_url)
            except Exception as error:
                print(f"Failed to download statement {statement_metadata['payDate']}: {error}")
                break

        print("Saving statement cache...")
        self.store_cache_file('adp_statement_cache.json', statement_data)
        return statement_data

    def store_statement_data_as_csv(self, statement_data, desired_fields = None):
        """Store statement data as a CSV file."""
        if desired_fields is None:
            fields = set()
            for statement in statement_data.values():
                fields.update(statement.keys())
            desired_fields = fields

        statements = list(statement_data.values())
        statements = sorted(statements, key=lambda statement: statement['payDate'])

        with open('adp_statements.csv', 'w') as f:
            writer = csv.DictWriter(f, fieldnames=desired_fields)
            writer.writeheader()
            for statement in statements:
                writer.writerow({
                    field: statement.get(field, '')
                    for field in desired_fields
                })
