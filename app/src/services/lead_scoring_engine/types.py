from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MatchedScoringRule:
    """One scoring rule that matched during lead computation."""

    rule_name: str
    score_delta: int


@dataclass(frozen=True)
class ScoreComputationBreakdown:
    """Score contribution and matched rules for one scoring dimension."""

    score_delta: int
    matched_rules: tuple[MatchedScoringRule, ...]


@dataclass(frozen=True)
class LeadScoringComputationResult:
    """Final persisted computation result for one lead inside a tenant run."""

    lead_id: UUID
    status: str
    previous_score: int
    raw_score: int
    final_score: int
    previous_stage: str
    new_stage: str
    is_stage_manually_overridden: bool
    is_skipped: bool
    matched_rule_names: tuple[str, ...]
