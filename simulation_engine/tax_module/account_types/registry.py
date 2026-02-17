from typing import Dict, Type, Optional
from .base import AccountType
from .new_zealand import NewZealandBaseAccount

# Registry maps jurisdiction string → AccountType class
ACCOUNT_TYPE_REGISTRY: Dict[str, Type[AccountType]] = {
    "nz": NewZealandBaseAccount,
    # Future jurisdictions can be added here:
    # "au": AustralianSuperAccount,
    # "us": USRetirementAccount,
}


def get_account_type(jurisdiction: str) -> Optional[Type[AccountType]]:
    """
    Get AccountType class for a jurisdiction.
    
    Args:
        jurisdiction: Tax jurisdiction string (e.g., "nz", "au")
        
    Returns:
        AccountType class for the jurisdiction, or None if not found
    """
    return ACCOUNT_TYPE_REGISTRY.get(jurisdiction)

