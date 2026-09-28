from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, desc, case
from app.models.inspection import Inspection
from app.models.product import Product
from app.models.report import InspectionReport
from app.models.rule_evaluation import RuleEvaluation
from app.models.adjudication import OCRAdjudication
from app.models.enums import InspectionOverallStatus, RuleOutcome
from app.schemas.analytics import (
    AnalyticsOverview,
    TrendDataPoint,
    OutcomeDistribution,
    CategoryDistributionItem,
    LocationDistributionItem,
    AdjudicationActivityItem,
)

async def get_analytics_overview(db: AsyncSession) -> AnalyticsOverview:
    now = datetime.now(timezone.utc)
    first_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    week_ago = now - timedelta(days=7)

    # Total inspections
    total_insps = (await db.execute(select(func.count()).select_from(Inspection))).scalar_one() or 0

    # This month
    insps_month = (
        await db.execute(
            select(func.count()).select_from(Inspection).where(Inspection.initiated_at >= first_of_month)
        )
    ).scalar_one() or 0

    # This week
    insps_week = (
        await db.execute(
            select(func.count()).select_from(Inspection).where(Inspection.initiated_at >= week_ago)
        )
    ).scalar_one() or 0

    # Products inspected
    prods_inspected = (
        await db.execute(
            select(func.count(func.distinct(Inspection.product_id)))
            .select_from(Inspection)
            .where(Inspection.product_id.isnot(None))
        )
    ).scalar_one() or 0

    # Reports generated
    total_reports = (await db.execute(select(func.count()).select_from(InspectionReport))).scalar_one() or 0

    # Inspections requiring review
    pending_review = (
        await db.execute(
            select(func.count())
            .select_from(Inspection)
            .where(
                Inspection.overall_status.in_([
                    InspectionOverallStatus.PENDING,
                    InspectionOverallStatus.PROCESSING,
                    InspectionOverallStatus.IN_REVIEW,
                ])
            )
        )
    ).scalar_one() or 0

    # Rule outcomes breakdown
    outcomes_q = (
        select(RuleEvaluation.outcome, func.count())
        .group_by(RuleEvaluation.outcome)
    )
    outcome_rows = (await db.execute(outcomes_q)).all()
    rule_outcomes: Dict[str, int] = {"PASS": 0, "REVIEW": 0, "FAIL": 0, "UNCERTAIN": 0}
    for verd, cnt in outcome_rows:
        key = verd.value if hasattr(verd, "value") else str(verd)
        if key == "INDETERMINATE":
            key = "UNCERTAIN"
        if key in rule_outcomes:
            rule_outcomes[key] = cnt

    # Total human adjudications & by type
    total_adj = (await db.execute(select(func.count()).select_from(OCRAdjudication))).scalar_one() or 0

    adj_type_q = (
        select(OCRAdjudication.correction_type, func.count())
        .group_by(OCRAdjudication.correction_type)
    )
    adj_type_rows = (await db.execute(adj_type_q)).all()
    adj_by_type: Dict[str, int] = {}
    for ctype, cnt in adj_type_rows:
        key = ctype.value if hasattr(ctype, "value") else str(ctype)
        adj_by_type[key] = cnt

    return AnalyticsOverview(
        total_inspections=total_insps,
        inspections_this_month=insps_month,
        inspections_this_week=insps_week,
        products_inspected=prods_inspected,
        reports_generated=total_reports,
        inspections_requiring_review=pending_review,
        rule_evaluation_outcomes=rule_outcomes,
        total_adjudications=total_adj,
        adjudications_by_type=adj_by_type,
    )

async def get_inspections_trend(db: AsyncSession, days: int = 30) -> List[TrendDataPoint]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    date_col = cast(Inspection.initiated_at, Date)
    query = (
        select(date_col.label("insp_date"), func.count().label("cnt"))
        .where(Inspection.initiated_at >= cutoff)
        .group_by(date_col)
        .order_by(date_col.asc())
    )
    rows = (await db.execute(query)).all()
    return [TrendDataPoint(date=r.insp_date.isoformat(), count=r.cnt) for r in rows]

async def get_outcomes_breakdown(db: AsyncSession) -> OutcomeDistribution:
    query = select(RuleEvaluation.outcome, func.count()).group_by(RuleEvaluation.outcome)
    rows = (await db.execute(query)).all()
    counts = {"PASS": 0, "REVIEW": 0, "FAIL": 0, "UNCERTAIN": 0}
    total = 0
    for verd, cnt in rows:
        key = verd.value if hasattr(verd, "value") else str(verd)
        if key == "INDETERMINATE":
            key = "UNCERTAIN"
        if key in counts:
            counts[key] = cnt
        total += cnt

    return OutcomeDistribution(
        pass_count=counts["PASS"],
        review_count=counts["REVIEW"],
        fail_count=counts["FAIL"],
        uncertain_count=counts["UNCERTAIN"],
        total_evaluations=total,
    )

async def get_categories_breakdown(db: AsyncSession) -> List[CategoryDistributionItem]:
    query = (
        select(
            func.coalesce(Product.category, 'Uncategorized').label("cat"),
            func.count(Inspection.id).label("cnt")
        )
        .join(Inspection, Inspection.product_id == Product.id, isouter=True)
        .group_by("cat")
        .order_by(desc("cnt"))
        .limit(10)
    )
    rows = (await db.execute(query)).all()
    total = sum(r.cnt for r in rows) or 1
    return [
        CategoryDistributionItem(
            category=r.cat,
            count=r.cnt,
            percentage=round((r.cnt / total) * 100, 1),
        )
        for r in rows
    ]

async def get_locations_breakdown(db: AsyncSession) -> List[LocationDistributionItem]:
    query = (
        select(
            func.coalesce(Inspection.retail_outlet_name, 'Field Sites / Unspecified').label("outlet"),
            func.count(Inspection.id).label("total_cnt"),
            func.sum(case((Inspection.overall_status == InspectionOverallStatus.COMPLIANT, 1), else_=0)).label("pass_cnt"),
            func.sum(case((Inspection.overall_status == InspectionOverallStatus.NON_COMPLIANT, 1), else_=0)).label("fail_cnt"),
            func.sum(case((Inspection.overall_status == InspectionOverallStatus.IN_REVIEW, 1), else_=0)).label("review_cnt"),
        )
        .group_by("outlet")
        .order_by(desc("total_cnt"))
        .limit(10)
    )
    rows = (await db.execute(query)).all()
    return [
        LocationDistributionItem(
            location=r.outlet,
            count=r.total_cnt,
            pass_count=int(r.pass_cnt or 0),
            fail_count=int(r.fail_cnt or 0),
            review_count=int(r.review_cnt or 0),
        )
        for r in rows
    ]

async def get_adjudication_activity(db: AsyncSession) -> List[AdjudicationActivityItem]:
    date_col = cast(OCRAdjudication.created_at, Date)
    query = (
        select(
            date_col.label("adj_date"),
            OCRAdjudication.correction_type,
            func.count().label("cnt")
        )
        .group_by(date_col, OCRAdjudication.correction_type)
        .order_by(desc(date_col))
        .limit(30)
    )
    rows = (await db.execute(query)).all()
    return [
        AdjudicationActivityItem(
            date=r.adj_date.isoformat(),
            correction_type=r.correction_type.value if hasattr(r.correction_type, "value") else str(r.correction_type),
            count=r.cnt,
        )
        for r in rows
    ]
