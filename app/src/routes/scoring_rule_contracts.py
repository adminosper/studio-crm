from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from src.models.scoring_rule_contract import ScoringRuleContractResponse
from src.services.lead_scoring_rules.contracts.service import ScoringRuleContractService
from src.shared.dependencies import get_scoring_rule_contract_service

router = APIRouter(prefix="/api/core/scoring-rule-contracts", tags=["core-scoring-rule-contracts"])


@router.get("", response_model=list[ScoringRuleContractResponse])
def list_scoring_rule_contracts(
    contract_service: ScoringRuleContractService = Depends(get_scoring_rule_contract_service),
) -> list[ScoringRuleContractResponse]:
    """Return all available versioned scoring-rule contracts."""
    return [ScoringRuleContractResponse.model_validate(contract) for contract in contract_service.list_contracts()]


@router.get("/{rule_type}", response_model=list[ScoringRuleContractResponse])
def list_scoring_rule_contracts_by_type(
    rule_type: Literal["fit", "behavior"],
    contract_service: ScoringRuleContractService = Depends(get_scoring_rule_contract_service),
) -> list[ScoringRuleContractResponse]:
    """Return all available contract versions for one rule type."""
    return [
        ScoringRuleContractResponse.model_validate(contract)
        for contract in contract_service.list_contracts_by_type(rule_type)
    ]
