import os
from typing import Optional, Dict, Any, List
from datetime import date
from csv import DictWriter

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

        file_exists = os.path.exists(output_path)
        fp = open(output_path, 'a+')
        csv_writer = DictWriter(
            fp,
            fieldnames=override_fieldnames if override_fieldnames else self.get_fieldnames(output_name),
            lineterminator='\n')

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
