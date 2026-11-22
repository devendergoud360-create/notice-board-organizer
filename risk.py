"""Novel algorithm: Notice Risk & Priority Score (NRPS).

Mathematical specification (see docs/SRS.md section 12). Deterministic,
dependency-free, bounded in [0, 1]. The implementation here is the reference;
an identical implementation exists in web/parity/risk.js and the parity check
verifies both produce the same value for a shared fixture set.

Steps
-----
Given a notice with expiry E, posted date P, lowercase category C, today T,
and the set of all notices with id < this.id:

  urgency         = clamp01(1 - (E - T).days / 30)   # overdue => 1
  staleness       = clamp01((T - P).days / 90)
  category_weight = (FNV1a_32(UTF8(C)) mod 1000) / 1000
  history_factor  = 0.5 + 0.5 * (expired_or_overdue_same_category / max(1, prior_same_category))
  score           = clamp01(0.45*urgency + 0.20*staleness
                            + 0.20*category_weight + 0.15*history_factor)
  output          = round_half_up(score, 6)

History is computed over lower-id records only, making the score stable and
reproducible for a given dataset ordering.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

FNV_OFFSET = 2166136261
FNV_PRIME = 16777619
MASK32 = 0xFFFFFFFF

WEIGHT_URGENCY = 0.45
WEIGHT_STALENESS = 0.20
WEIGHT_CATEGORY = 0.20
WEIGHT_HISTORY = 0.15


def clamp01(value: float) -> float:
    """Clamp a real number into the closed interval [0, 1]."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def fnv1a_32(text: str) -> int:
    """FNV-1a 32-bit hash of the UTF-8 bytes of text."""
    h = FNV_OFFSET
    for byte in text.lower().encode("utf-8"):
        h = (h * FNV_PRIME) & MASK32
        h ^= byte
        h &= MASK32
    return h


def round_half_up(value: float, places: int = 6) -> float:
    """Round using ROUND_HALF_UP (matches many languages' decimal rounding)."""
    quant = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def _days_until_expiry(expiry: date, today: date) -> int:
    return (expiry - today).days


def urgency_component(expiry: date, today: date) -> float:
    days = _days_until_expiry(expiry, today)
    if days < 0:
        return 1.0
    return clamp01(1 - days / 30.0)


def staleness_component(posted: date, today: date) -> float:
    return clamp01((today - posted).days / 90.0)


def category_component(category: str) -> float:
    return (fnv1a_32(category) % 1000) / 1000.0


def history_component(
    notice_id: int,
    category: str,
    records: Sequence,
    today: date,
) -> float:
    """History-aware factor over records with lower id and same category."""
    cat = category.lower()
    prior = [
        r for r in records
        if r.id < notice_id and r.category.lower() == cat
    ]
    if not prior:
        return 0.5
    bad = 0
    for r in prior:
        days = _days_until_expiry(r.expiry_date, today)
        if days < 0 or r.status == "Expired":
            bad += 1
    ratio = bad / len(prior)
    return 0.5 + 0.5 * ratio


def compute_risk(
    notice,
    records: Sequence,
    today: date | None = None,
) -> float:
    """Compute the NRPS for one notice against a dataset (0..1, 6 decimals)."""
    today = today or date.today()
    urgency = urgency_component(notice.expiry_date, today)
    staleness = staleness_component(notice.date_posted, today)
    catw = category_component(notice.category)
    hist = history_component(notice.id, notice.category, records, today)
    score = (
        WEIGHT_URGENCY * urgency
        + WEIGHT_STALENESS * staleness
        + WEIGHT_CATEGORY * catw
        + WEIGHT_HISTORY * hist
    )
    return round_half_up(clamp01(score), 6)


def risk_breakdown(notice, records, today: date | None = None) -> dict:
    """Return all components plus the final score (for explainability)."""
    today = today or date.today()
    return {
        "notice_id": notice.id,
        "urgency": round_half_up(urgency_component(notice.expiry_date, today), 6),
        "staleness": round_half_up(staleness_component(notice.date_posted, today), 6),
        "category_weight": round_half_up(category_component(notice.category), 6),
        "history_factor": round_half_up(
            history_component(notice.id, notice.category, records, today), 6
        ),
        "risk_score": compute_risk(notice, records, today),
    }
