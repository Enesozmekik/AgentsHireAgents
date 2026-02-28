from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


CATEGORY_KEYWORDS = {
    "DEVELOPMENT": ("code", "api", "contract", "backend", "frontend", "integration", "debug"),
    "RESEARCH": ("research", "analyze", "report", "trend", "market", "review"),
    "DATA_MINING": ("data", "scrape", "dataset", "extract", "pipeline", "etl"),
    "CONTENT_GEN": ("content", "write", "post", "summary", "copy", "article"),
}


@dataclass(frozen=True)
class Candidate:
    address: str
    category: str
    base_fee_wei: int
    reputation_score: int

    @property
    def efficiency(self) -> float:
        if self.base_fee_wei <= 0:
            return 0.0
        return self.reputation_score / float(self.base_fee_wei)


@dataclass(frozen=True)
class SelectionResult:
    category: str
    best: Candidate
    reason: str
    candidates: List[Candidate]


def infer_category(prompt: str, default: str = "RESEARCH") -> str:
    lowered = (prompt or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return default


def rank_candidates(candidates: Iterable[Candidate], budget_wei: int) -> List[Candidate]:
    filtered = [c for c in candidates if c.base_fee_wei <= budget_wei]
    # Goal: maximize quality (reputation) within budget.
    # Tie-breakers: cheaper fee first, then better efficiency.
    filtered.sort(key=lambda c: (-c.reputation_score, c.base_fee_wei, -c.efficiency))
    return filtered


def select_best(candidates: Iterable[Candidate], category: str, budget_wei: int) -> SelectionResult:
    ranked = rank_candidates(candidates, budget_wei)
    if not ranked:
        raise ValueError(f"No eligible agent for category={category} and budgetWei={budget_wei}")

    best = ranked[0]
    reason = (
        f"Agent {best.address} selected because it has the highest quality score "
        f"(reputation={best.reputation_score}) under budget {budget_wei}; "
        f"ties are broken by lower base fee."
    )
    return SelectionResult(category=category, best=best, reason=reason, candidates=ranked)
