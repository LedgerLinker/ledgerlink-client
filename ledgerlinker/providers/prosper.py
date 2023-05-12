"""A provider for Prosper.com investment marketplace."""
from typing import List, Optional, Dict
from csv import DictWriter
import requests
from datetime import date
from .base import Provider, ProviderException
import sys


class ProsperProvider(Provider):

    def __init__(self, config, prosper_client=None):
        self.config = config
        if not self.load_dependency():
            raise ProviderException(
                'Cannot use Prosper Provider because Prosper API lib not installed. Please install the prosper package.'
                'pip install prosper'
            )

        if prosper_client:
            self.prosper_client = prosper_client
        else:
            self.prosper_client = self.prosper_api_class.get_client_by_username_password(
                client_id=config.client_id,
                client_secret=config.client_secret,
                username=config.username,
                password=config.password)

    def load_dependency(self):
        try:
            from prosper import ProsperAPI
            self.prosper_api_class = ProsperAPI
        except ModuleNotFoundError:
            return False
        return True

    def fetch_purchases(self, start_date : Optional[date] = None) -> List[Dict]:
        """Fetch purchases from Prosper."""

        notes = self.prosper_client.notes()

        purchases = []
        for note in sorted(notes, key=lambda x: x['origination_date']):
            rate = round(note['borrower_rate'] * 100, 2)
            row = {
                "date": note['origination_date'],
                "loan_note_id": note['loan_note_id'],
                "loan_amount": note['amount_borrowed'],
                "term": note['term'],
                "rate": rate,
                "note_amount": note['note_ownership_amount'],
                "prosper_rating": note['prosper_rating']
            }

            if start_date:
                if row['date'] < start_date:
                    continue

            purchases.append(row)

        return purchases


    def get_fieldnames(self, output_name):
        if output_name == 'purchases':
            return [
                'date',
                'loan_note_id',
                'note_amount',
                'loan_amount',
                'term',
                'rate',
                'prosper_rating'
            ]

    def sync(self, last_links : Optional[Dict[str, date]] = None):
        """Sync the prosper provider."""

        self.register_output('purchases', 'prosper-purchases.csv')

        purchases = self.fetch_purchases(
            start_date=last_links['prosper'] if last_links else None)
        self.store('purchases', purchases)
