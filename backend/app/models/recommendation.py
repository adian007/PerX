"""Internal recommendation data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RecommenderMode = Literal["cold_start", "warm"]

CATEGORIES = [
    "fitness",
    "travel",
    "wellness",
    "food",
    "education",
    "entertainment",
    "transport",
    "childcare",
    "other",
]


@dataclass(frozen=True)
class Provider:
    """Provider data needed by recommendation responses."""

    id: str
    company_name: str
    logo_url: str | None = None
    avg_rating: float = 0.0


@dataclass(frozen=True)
class Perk:
    """Perk data needed by recommendation scoring."""

    id: str
    name: str
    category: str
    short_description: str
    image_url: str | None
    employee_price_cents: int
    provider: Provider
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    is_featured: bool = False
    popularity_score: float = 0.5
    quality_score: float = 0.5
    collaborative_score: float = 0.0


@dataclass(frozen=True)
class EmployeeProfile:
    """Employee data needed by the recommendation engine."""

    id: str
    first_name: str
    interaction_count: int
    recommender_mode: RecommenderMode = "cold_start"
    lifestyle_tags: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    budget_sensitivity: str = "medium"
    wellness_priority: int = 5
    family_situation: str = "single"
    affinity_vector: dict[str, float] | None = None


@dataclass(frozen=True)
class ScoreBreakdown:
    """Warm-mode score breakdown."""

    content_score: float
    cf_score: float
    ucb_bonus: float
    final_score: float


@dataclass(frozen=True)
class ScoredRecommendation:
    """A scored recommendation ready for API serialization."""

    perk: Perk
    recommendation_score: float
    reason_code: str
    reason_text: str
    is_affordable: bool
    score_breakdown: ScoreBreakdown | None = None

    def to_api_dict(self, include_score_breakdown: bool = False) -> dict[str, Any]:
        """Serialize the recommendation using the public API contract shape."""

        public_score = round(self.recommendation_score, 3)
        data: dict[str, Any] = {
            "id": self.perk.id,
            "name": self.perk.name,
            "category": self.perk.category,
            "short_description": self.perk.short_description,
            "image_url": self.perk.image_url,
            "employee_price_cents": self.perk.employee_price_cents,
            "employee_price_formatted": f"EUR {self.perk.employee_price_cents / 100:.2f}",
            "provider": {
                "id": self.perk.provider.id,
                "company_name": self.perk.provider.company_name,
                "logo_url": self.perk.provider.logo_url,
                "avg_rating": self.perk.provider.avg_rating,
            },
            "recommendation_score": public_score,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "tags": self.perk.tags,
            "is_affordable": self.is_affordable,
            "is_featured": self.perk.is_featured,
        }
        if include_score_breakdown and self.score_breakdown is not None:
            data["score_breakdown"] = {
                "content_score": self.score_breakdown.content_score,
                "cf_score": self.score_breakdown.cf_score,
                "ucb_bonus": self.score_breakdown.ucb_bonus,
                "final_score": public_score,
            }
        return data
