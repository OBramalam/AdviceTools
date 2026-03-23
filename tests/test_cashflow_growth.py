from datetime import datetime

from schemas.base_schemas import CashFlow, FinancialPlan
from services.cashflow_service import CashflowService


def _plan() -> FinancialPlan:
    return FinancialPlan(
        id=1,
        user_id=1,
        name="Plan",
        description="Plan",
        start_age=30,
        retirement_age=65,
        plan_end_age=31,
        plan_start_date=datetime(2026, 1, 1),
        portfolio_target_value=1000000.0,
    )


def test_growth_override_applies_to_monthly_fixed_recurring():
    service = CashflowService(use_monthly_steps=True)
    plan = _plan()
    cf = CashFlow(
        id=1,
        plan_id=1,
        portfolio_id=None,
        name="Salary",
        description="Salary",
        amount=100.0,
        growth_rate=0.05,
        periodicity="monthly",
        frequency=1,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 3, 1),
        basis="fixed",
        include_in_main_savings=True,
    )

    ctx = service.build_plan_cashflow_context(plan, [cf], annual_inflation=0.02)
    monthly_factor = ((1.0 + 0.05) / (1.0 + 0.02)) ** (1.0 / 12.0)

    assert abs(ctx.income_per_step[0] - 100.0) < 1e-9
    assert abs(ctx.income_per_step[1] - (100.0 * monthly_factor)) < 1e-9
    assert abs(ctx.income_per_step[2] - (100.0 * (monthly_factor ** 2))) < 1e-9


def test_growth_override_not_applied_to_irregular_recurring():
    service = CashflowService(use_monthly_steps=True)
    plan = _plan()
    cf = CashFlow(
        id=2,
        plan_id=1,
        portfolio_id=None,
        name="Annual bonus",
        description="Bonus",
        amount=1200.0,
        growth_rate=0.08,
        periodicity="annually",
        frequency=1,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2027, 1, 1),
        basis="fixed",
        include_in_main_savings=True,
    )

    ctx = service.build_plan_cashflow_context(plan, [cf], annual_inflation=0.02)

    assert abs(ctx.income_per_step[0] - 1200.0) < 1e-9
    # Second annual occurrence remains unchanged in V1.
    assert abs(ctx.income_per_step[12] - 1200.0) < 1e-9
