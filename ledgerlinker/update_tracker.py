import sys
from typing import Dict, Optional
from datetime import date
from json import JSONDecodeError
import json


class LastUpdateTracker:
    """Tracks the last time each provider export was synced."""

    def __init__(self, last_link_path : str):
        self.last_link_path = last_link_path
        self.last_links = self._load_last_link_file(last_link_path)

    def get(self, export_name : str) -> Optional[date]:
        """Get the last time the given export was synced."""
        return self.last_links.get(export_name, None)

    def update(self, export_name : str, latest_date : Optional[date]):
        """Update the last link file with the latest date for the given export."""

        self.last_links[export_name] = latest_date
        self._update_last_link_file(self.last_link_path, self.last_links)

    def _update_last_link_file(self, last_link_path : str, latest_transaction_by_export_id : dict):
        """Update the last link file which contains the last time each export was synced."""
        with open(self.last_link_path, 'w') as config_file:

            config_file.write(json.dumps({
                export_id: latest_transaction.isoformat()
                for export_id, latest_transaction in latest_transaction_by_export_id.items()
            }))

    def _load_last_link_file(self, last_link_path) -> Dict[str, date]:
        """Load lastlink file which contains the last time each export was synced."""
        try:
            with open(last_link_path, 'r') as last_links_fp:
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
                print(
                    f'The last link file is corrupt. Please delete it and try again.'
                    f' The invalid key is "{link_slug}".'
                )
                sys.exit(1)

        return last_links_by_export_slug
