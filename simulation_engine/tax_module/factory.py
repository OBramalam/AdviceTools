from typing import Dict, Any, Optional
from .account_types.base import AccountType
from .account_types.registry import get_account_type


def create_tax_model(tax_model_config: Optional[Dict[str, Any]]) -> Optional[AccountType]:
    """
    Factory function to instantiate appropriate AccountType from tax config.
    
    Args:
        tax_model_config: Dict with 'jurisdiction' key and jurisdiction-specific params.
                          If None, returns None (no tax).
        
    Returns:
        Instantiated AccountType instance, or None if no tax
        
    Raises:
        ValueError: If jurisdiction is unknown or required params are missing
    """
    if not tax_model_config:
        return None
    
    jurisdiction = tax_model_config.get("jurisdiction")
    if not jurisdiction:
        return None
    
    # Get AccountType class from registry
    account_type_class = get_account_type(jurisdiction)
    if not account_type_class:
        raise ValueError(f"Unknown tax jurisdiction: {jurisdiction}")
    
    # Instantiate with jurisdiction-specific params (excluding 'jurisdiction' key)
    config_without_jurisdiction = {k: v for k, v in tax_model_config.items() if k != "jurisdiction"}
    
    if jurisdiction == "nz":
        return account_type_class(
            pir_rate=config_without_jurisdiction["pir_rate"],
            marginal_tax_rate=config_without_jurisdiction["marginal_tax_rate"],
            percent_pie_fund=config_without_jurisdiction["percent_pie_fund"],
            percent_fif_fund=config_without_jurisdiction["percent_fif_fund"],
        )
    else:
        raise ValueError(f"Tax model instantiation not implemented for jurisdiction: {jurisdiction}")

