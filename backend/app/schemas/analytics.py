from datetime import date, datetime
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AnalyticsOverview(BaseModel):
    total_inspections: int
    inspections_this_month: int
    inspections_this_week: int
    products_inspected: int
    reports_generated: int
    inspections_requiring_review: int
    rule_evaluation_outcomes: Dict[str, int]
    total_adjudications: int
    adjudications_by_type: Dict[str, int]

class TrendDataPoint(BaseModel):
    date: str
    count: int

class OutcomeDistribution(BaseModel):
    pass_count: int
    review_count: int
    fail_count: int
    uncertain_count: int
    total_evaluations: int

class CategoryDistributionItem(BaseModel):
    category: str
    count: int
    percentage: float

class LocationDistributionItem(BaseModel):
    location: str
    count: int
    pass_count: int
    fail_count: int
    review_count: int

class AdjudicationActivityItem(BaseModel):
    date: str
    correction_type: str
    count: int
