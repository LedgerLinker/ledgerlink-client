import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from csv import DictWriter, DictReader

from ledgerlinker.update_tracker import LastUpdateTracker


class ProviderException(Exception):
    pass


class ProviderConfig:
    """Configuration for a provider."""
    def __init__(
        self,
        name : str,
        output_dir : str,
        **extra_options : Dict
    ):
        self.name = name
        self.output_dir = output_dir
        if extra_options:
            for key,value in extra_options.items():
                setattr(self, key, value)


class Provider:
    """Base class for a provider."""

    def __init__(self, config : ProviderConfig):
        self.config = config

    def get_fieldnames(self, output_name):
        return self.config['fields']

    def check_file_exists_and_get_existing_fieldnames(self, path : str) -> Tuple[bool, Optional[str]]:
        """Check if the file exists and has the correct fieldnames."""
        if not os.path.exists(path):
            return False, None

        with open(path, 'r') as fp:
            csv_reader = DictReader(fp)
            fieldnames = csv_reader.fieldnames

        return True, fieldnames

    def register_output(
        self,
        output_name : str,
        output_file_name : str,
        override_fieldnames : Optional[List[str]] = None
    ):
        if not hasattr(self, '_outputs'):
            self._outputs : Dict[str, Dict] = {}

        if output_name in self._outputs:
            raise ProviderException(f'Output {output_name} already registered.')

        os.makedirs(self.config.output_dir, exist_ok=True)

        output_path = os.path.join(self.config.output_dir, output_file_name)
        file_exists, fieldnames = self.check_file_exists_and_get_existing_fieldnames(output_path)

        expected_fieldnames = override_fieldnames if override_fieldnames else self.get_fieldnames(output_name)
        if not fieldnames:
            fieldnames = expected_fieldnames

        if fieldnames != expected_fieldnames:
            print('Warning: fieldnames in existing file do not match expected fieldnames. Using existing file fields.')

        fp = open(output_path, 'a+')
        csv_writer = DictWriter(
            fp,
            fieldnames=fieldnames,
            lineterminator='\n',
            extrasaction='ignore')

        if not file_exists:
            csv_writer.writeheader()

        self._outputs[output_name] = {
            'path': output_path,
            'fp': fp,
            'csv_writer': csv_writer
        }

    def store(self, output_name : str, rows : List[Dict]):
        for row in rows:
            self.store_row(output_name, row)

    def store_row(self, output_name, data: dict):
        if not hasattr(self, '_outputs'):
            raise ProviderException('No outputs registered.')

        if output_name not in self._outputs:
            raise ProviderException(f'Output {output_name} not registered.')

        self._outputs[output_name]['csv_writer'].writerow(data)

    def close(self):
        if not hasattr(self, '_outputs'):
            return

        for output in self._outputs.values():
            output['fp'].close()


    def sync(self, last_links : LastUpdateTracker):
        """Sync the provider."""
        raise ProviderException(f'Provider {self} does not implement sync.')
