# models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

currency_unit = "INR"


class Idea(BaseModel):
    id: str
    title: str
    short_description: str
    novelty_points: List[str] = []


class MarketResearch(BaseModel):
    market_size_inr: float = Field(..., description="Total Addressable Market (INR)")
    growth_cagr_pct: float
    competitors: List[Dict[str, Any]] = []
    swot: Dict[str, List[str]] = {}
    supporting_links: List[str] = []


class Financials(BaseModel):
    year_wise_revenue_inr: Dict[str, float]
    year_wise_costs_inr: Dict[str, float]
    burn_rate_monthly_inr: float
    runway_months: float
    funding_required_inr: float
    assumptions: Dict[str, Any] = {}


class LegalCompliance(BaseModel):
    required_licenses: List[str] = []
    data_protection_actions: List[str] = []
    sector_regs: List[str] = []
    next_steps: List[str] = []


class PitchDeck(BaseModel):
    slides: List[Dict[str, Any]] = []


class Strategy(BaseModel):
    milestones: List[Dict[str, Any]] = []
    team_needed: List[str] = []
    go_to_market: Dict[str, Any] = {}


class StartupOutput(BaseModel):
    domain: str
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ideas: List[Idea] = []
    market_research: Dict[str, Any] = {}
    financials: Dict[str, Any] = {}
    legal: Dict[str, Any] = {}
    pitch_deck: Dict[str, Any] = {}
    strategy: Dict[str, Any] = {}

    model_config = {"arbitrary_types_allowed": True}
