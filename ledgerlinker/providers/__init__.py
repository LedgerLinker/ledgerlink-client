from typing import Dict, List
from .base import Provider, ProviderConfig
from .prosper import ProsperProvider
from .adp import ADPProvider
from .ledgerlinker_service import LedgerLinkerServiceProvider

PROVIDERS = {
        'prosper': ProsperProvider,
        'adp': ADPProvider,
        'ledgerlinker': LedgerLinkerServiceProvider
}

def get_available_providers() -> Dict[str, Provider]:
    return PROVIDERS

def get_providers(provider_configs : Dict[str, ProviderConfig]) -> Dict[str, Provider]:
    """Return a list of instantiated providers for the passed provider configs."""
    providers = {}
    available_providers = get_available_providers()

    for provider_name, provider_config in provider_configs.items():
        provider_class = available_providers[provider_config.provider]
        provider = provider_class(provider_config)
        providers[provider_name] = provider

    return providers
