"""Provider to download ADP pay statements."""
import json
import requests
import csv

class ADPProvider:
    pass

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

    def get_statement_list(self):
        """Retrieve a list of available statements from ADP."""
        result = self.get(self.STATEMENT_LIST_URL)
        return result['payStatements']

    def load_cache_file(self, cache_file_path):
        try:
            with open(cache_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def store_cache_file(self, cache_file_path, data):
        with open(cache_file_path, 'w') as f:
            json.dump(data, f)

    def download_all_statements(self, flush_cache=False):

        if flush_cache:
            statement_data = {}
        else:
            statement_data = self.load_cache_file('adp_statement_cache.json')

        available_statements = self.get_statement_list()
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

    def store_statement_data_as_csv(self, desired_fields = None):
        with open('adp_statement_cache.json', 'r') as f:
            statement_data = json.load(f)

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
