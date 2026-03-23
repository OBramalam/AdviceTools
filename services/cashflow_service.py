from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta

from schemas import FinancialPlan, CashFlow as CashFlowSchema, PortfolioConfig
from simulation_engine.common.types import CashFlow as SimulationCashFlow
from common.enums import CashFlowPeriodicity


@dataclass
class PlanCashflowContext:
    """
    Plan-level cashflow context on the discrete simulation grid.

    This captures income, expenses, and net savings per step, as well as
    a sparse step-function representation of shared savings and irregular
    transactions suitable for passing into the simulation engine.
    """

    plan_start_year: int
    plan_end_year: int
    end_step: int

    income_per_step: Dict[int, float]
    expense_per_step: Dict[int, float]
    net_savings_per_step: Dict[int, float]
    income_by_id: Dict[int, Dict[int, float]]

    shared_savings_rates: List[SimulationCashFlow]
    shared_transactions: List[SimulationCashFlow]

    # Per-portfolio deductions from main savings due to percentage-based
    # portfolio-specific rules with strict "deduct from savings" semantics.
    # Keyed by portfolio_id then step index.
    deductions_by_portfolio: Dict[int, Dict[int, float]]


@dataclass
class PortfolioCashflowStreams:
    """
    Final cashflow streams for a single portfolio in the format expected
    by the simulation engine.
    """

    savings_rates: List[SimulationCashFlow]
    transactions: List[SimulationCashFlow]


class CashflowService:
    """
    Service responsible for building plan-level and portfolio-level cashflow
    streams on the simulation grid.

    This encapsulates all the complexity around:
    - plan-level main cashflows (income, expenses, net savings)
    - portfolio-specific cashflows (fixed amounts and, eventually, percentage rules)
    - periodicity / frequency / date-to-step mapping
    - building sparse `SimulationCashFlow` step-functions for the engine
    """

    def __init__(self, use_monthly_steps: bool = True) -> None:
        self.use_monthly_steps = use_monthly_steps

    def _step_growth_factor(
        self,
        cashflow_annual_growth: Optional[float],
        annual_inflation: float,
    ) -> float:
        """
        Compute per-step differential growth factor relative to global inflation.
        This avoids double-counting inflation when the engine inflates cashflows.
        """
        if cashflow_annual_growth is None:
            return 1.0
        steps_per_year = 12 if self.use_monthly_steps else 1
        return ((1.0 + cashflow_annual_growth) / (1.0 + annual_inflation)) ** (1.0 / steps_per_year)

    # -------------------------------------------------------------------------
    # Core helpers
    # -------------------------------------------------------------------------

    def _build_time_grid(
        self,
        financial_plan: FinancialPlan,
    ) -> tuple[int, int, int]:
        """
        Derive plan_start_year, plan_end_year, and end_step for the simulation grid.
        """
        plan_start_date = financial_plan.plan_start_date
        plan_end_date = plan_start_date + relativedelta(
            years=int(financial_plan.plan_end_age) - int(financial_plan.start_age)
        )
        plan_start_year = plan_start_date.year
        plan_end_year = plan_end_date.year

        steps_per_year = 12 if self.use_monthly_steps else 1
        end_step = (plan_end_year - plan_start_year) * steps_per_year
        return plan_start_year, plan_end_year, end_step

    def _date_to_step(self, date_obj: datetime.datetime, plan_start_year: int) -> int:
        """
        Map a datetime to a simulation step index.
        """
        if self.use_monthly_steps:
            year_diff = date_obj.year - plan_start_year
            month = date_obj.month - 1
            return year_diff * 12 + month
        else:
            return date_obj.year - plan_start_year

    def _normalize_periodicity(self, periodicity) -> CashFlowPeriodicity:
        """
        Normalize periodicity to enum, handling string values from database.
        Duplicated (for now) from SimulationService to keep this service
        self-contained. Eventually, this helper can be shared.
        """
        if isinstance(periodicity, str):
            try:
                return CashFlowPeriodicity(periodicity)
            except ValueError:
                return CashFlowPeriodicity.MONTHLY
        elif isinstance(periodicity, CashFlowPeriodicity):
            return periodicity
        else:
            return CashFlowPeriodicity.MONTHLY

    def _add_fixed_recurring_to_series(
        self,
        cf: CashFlowSchema,
        target: Dict[int, float],
        plan_start_year: int,
        end_step: int,
        annual_inflation: float,
    ) -> None:
        """
        Add a fixed recurring cashflow's amount into a per-step series, respecting
        periodicity and frequency.
        """
        if not cf.start_date or not cf.end_date:
            return

        periodicity = self._normalize_periodicity(
            getattr(cf, "periodicity", CashFlowPeriodicity.MONTHLY)
        )
        frequency = getattr(cf, "frequency", 1)
        apply_growth_override = periodicity == CashFlowPeriodicity.MONTHLY and frequency == 1
        start_step = self._date_to_step(cf.start_date, plan_start_year)
        growth_factor_per_step = self._step_growth_factor(
            getattr(cf, "growth_rate", None) if apply_growth_override else None,
            annual_inflation=annual_inflation,
        )

        if periodicity == CashFlowPeriodicity.MONTHLY:
            interval_months = frequency
        elif periodicity == CashFlowPeriodicity.QUARTERLY:
            interval_months = frequency * 3
        elif periodicity == CashFlowPeriodicity.ANNUALLY:
            interval_months = frequency * 12
        else:
            interval_months = frequency

        current_date = cf.start_date
        end_date_local = cf.end_date

        while current_date <= end_date_local:
            step = self._date_to_step(current_date, plan_start_year)
            if 0 <= step <= end_step:
                if apply_growth_override:
                    step_offset = max(0, step - start_step)
                    amount = cf.amount * (growth_factor_per_step ** step_offset)
                else:
                    amount = cf.amount
                target[step] = target.get(step, 0.0) + amount
            current_date = current_date + relativedelta(months=interval_months)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def build_plan_cashflow_context(
        self,
        financial_plan: FinancialPlan,
        cash_flows: List[CashFlowSchema],
        annual_inflation: float,
    ) -> PlanCashflowContext:
        """
        Build plan-level income, expenses, net savings, and shared sparse cashflows.

        This only considers:
        - plan-level cashflows (portfolio_id is None)
        - cashflows that participate in main savings (include_in_main_savings=True)
        - fixed basis (basis='fixed')

        Percentage-based rules and portfolio-specific flows are handled at the
        portfolio level on top of this shared context.
        """
        plan_start_year, plan_end_year, end_step = self._build_time_grid(financial_plan)

        income_per_step: Dict[int, float] = {}
        expense_per_step: Dict[int, float] = {}
        income_by_id: Dict[int, Dict[int, float]] = {}

        for cf in cash_flows or []:
            # Plan-level only
            if getattr(cf, "portfolio_id", None) is not None:
                continue
            if not getattr(cf, "include_in_main_savings", True):
                continue
            if getattr(cf, "basis", "fixed") != "fixed":
                continue

            if not cf.start_date or not cf.end_date:
                continue

            if cf.amount > 0:
                self._add_fixed_recurring_to_series(
                    cf, income_per_step, plan_start_year, end_step, annual_inflation
                )
                income_by_id.setdefault(cf.id, {})
                self._add_fixed_recurring_to_series(
                    cf, income_by_id[cf.id], plan_start_year, end_step, annual_inflation
                )
            elif cf.amount < 0:
                self._add_fixed_recurring_to_series(
                    cf, expense_per_step, plan_start_year, end_step, annual_inflation
                )

        net_savings_per_step: Dict[int, float] = {}
        for step in range(0, end_step + 1):
            income_val = income_per_step.get(step, 0.0)
            expense_val = expense_per_step.get(step, 0.0)
            net_savings_per_step[step] = income_val + expense_val

        # Apply portfolio-specific percentage-based rules that should strictly
        # deduct from main savings (e.g., super contributions as % of salary).
        deductions_by_portfolio: Dict[int, Dict[int, float]] = {}
        for cf in cash_flows or []:
            portfolio_id = getattr(cf, "portfolio_id", None)
            if portfolio_id is None:
                continue
            basis = getattr(cf, "basis", "fixed")
            if basis not in ("pct_total_income", "pct_specific_income", "pct_savings"):
                continue
            # Only strict-deduct rules participate here.
            if not getattr(cf, "include_in_main_savings", True) and basis != "pct_savings":
                continue
            if not cf.start_date or not cf.end_date:
                continue

            # Determine active step range for this rule.
            start_step = self._date_to_step(cf.start_date, plan_start_year)
            end_step_local = self._date_to_step(cf.end_date, plan_start_year)
            pct = cf.amount / 100.0

            for step in range(max(0, start_step), min(end_step_local, end_step) + 1):
                # Choose base value for this step.
                if basis == "pct_total_income":
                    base_val = income_per_step.get(step, 0.0)
                elif basis == "pct_specific_income":
                    ref_id = getattr(cf, "reference_cashflow_id", None)
                    if ref_id is None or ref_id not in income_by_id:
                        continue
                    base_val = income_by_id[ref_id].get(step, 0.0)
                else:  # "pct_savings" always treated as from main savings
                    base_val = net_savings_per_step.get(step, 0.0)

                if base_val == 0.0:
                    continue

                extra = pct * base_val
                if extra == 0.0:
                    continue

                # Reduce shared net savings at this step.
                net_savings_per_step[step] = net_savings_per_step.get(step, 0.0) - extra

                # Record deduction for this portfolio.
                portfolio_deductions = deductions_by_portfolio.setdefault(portfolio_id, {})
                portfolio_deductions[step] = portfolio_deductions.get(step, 0.0) + extra

        # Build a sparse step-function for shared savings rates from the adjusted net savings.
        shared_savings_rates: List[SimulationCashFlow] = []
        running_value: Optional[float] = None
        for step in range(0, end_step + 1):
            val = net_savings_per_step.get(step, 0.0)
            if running_value is None or val != running_value:
                shared_savings_rates.append(
                    SimulationCashFlow(step=float(step), value=val)
                )
                running_value = val

        # For now, this service does not attempt to split regular vs irregular at the
        # plan level; we treat all non-main-savings logic as portfolio-specific.
        shared_transactions: List[SimulationCashFlow] = []

        return PlanCashflowContext(
            plan_start_year=plan_start_year,
            plan_end_year=plan_end_year,
            end_step=end_step,
            income_per_step=income_per_step,
            expense_per_step=expense_per_step,
            net_savings_per_step=net_savings_per_step,
            income_by_id=income_by_id,
            shared_savings_rates=shared_savings_rates,
            shared_transactions=shared_transactions,
            deductions_by_portfolio=deductions_by_portfolio,
        )

    def build_portfolio_streams(
        self,
        plan_ctx: PlanCashflowContext,
        portfolios: List[PortfolioConfig],
        cash_flows: List[CashFlowSchema],
        annual_inflation: float,
    ) -> Dict[str, PortfolioCashflowStreams]:
        """
        Build per-portfolio cashflow streams in the engine format.

        NOTE: This initial implementation focuses on reproducing the current
        behaviour (plan-level main savings allocated by cashflow_allocation and
        portfolio-specific fixed cashflows as extra transactions). Percentage-based
        bases can be layered on top of this context in a follow-up step.
        """
        result: Dict[str, PortfolioCashflowStreams] = {}

        # Start from shared net savings and allocate by cashflow_allocation,
        # then apply portfolio-specific deductions and extra flows.
        for portfolio in portfolios:
            key = str(portfolio.id) if portfolio.id is not None else f"temp_{len(result)}"

            # Allocate main net savings to this portfolio.
            savings_per_step: Dict[int, float] = {}
            for step, net_val in plan_ctx.net_savings_per_step.items():
                savings_per_step[step] = net_val * portfolio.cashflow_allocation

            # Apply strict deduct-from-savings contributions that have been
            # recorded at the plan level for this portfolio.
            portfolio_deductions = plan_ctx.deductions_by_portfolio.get(
                portfolio.id or -1, {}
            )
            for step, extra in portfolio_deductions.items():
                savings_per_step[step] = savings_per_step.get(step, 0.0) + extra

            # Build sparse step-function for savings_rates.
            savings_rates: List[SimulationCashFlow] = []
            running_val: Optional[float] = None
            for step in range(0, plan_ctx.end_step + 1):
                val = savings_per_step.get(step, 0.0)
                if running_val is None or val != running_val:
                    savings_rates.append(
                        SimulationCashFlow(step=float(step), value=val)
                    )
                    running_val = val

            # Build portfolio-specific transactions from fixed and percentage-based
            # rules that do not affect the shared main savings pool (i.e. treated
            # as additional contributions/withdrawals).
            per_step_transactions: Dict[int, float] = {}

            for cf in cash_flows or []:
                if getattr(cf, "portfolio_id", None) != portfolio.id:
                    continue

                basis = getattr(cf, "basis", "fixed")

                # Fixed portfolio-specific cashflows as recurring transactions.
                if basis == "fixed":
                    self._add_fixed_recurring_to_series(
                        cf, per_step_transactions, plan_ctx.plan_start_year, plan_ctx.end_step, annual_inflation
                    )
                    continue

                # Percentage-based flows that are *not* strict-deduct from savings
                # (i.e. include_in_main_savings=False) are treated as additional
                # contributions/withdrawals.
                if basis in ("pct_total_income", "pct_specific_income", "pct_savings"):
                    if getattr(cf, "include_in_main_savings", True) and basis != "pct_savings":
                        # These have already been applied as strict-deduct at the plan level
                        # and routed to this portfolio via deductions_by_portfolio.
                        continue

                    if not cf.start_date or not cf.end_date:
                        continue

                    start_step = self._date_to_step(cf.start_date, plan_ctx.plan_start_year)
                    end_step_local = self._date_to_step(cf.end_date, plan_ctx.plan_start_year)
                    pct = cf.amount / 100.0

                    for step in range(
                        max(0, start_step), min(end_step_local, plan_ctx.end_step) + 1
                    ):
                        if basis == "pct_total_income":
                            base_val = plan_ctx.income_per_step.get(step, 0.0)
                        elif basis == "pct_specific_income":
                            ref_id = getattr(cf, "reference_cashflow_id", None)
                            if ref_id is None or ref_id not in plan_ctx.income_by_id:
                                continue
                            base_val = plan_ctx.income_by_id[ref_id].get(step, 0.0)
                        else:  # "pct_savings" treated as additional (non-deduct) here
                            base_val = plan_ctx.net_savings_per_step.get(step, 0.0)

                        if base_val == 0.0:
                            continue

                        extra = pct * base_val
                        if extra == 0.0:
                            continue

                        per_step_transactions[step] = per_step_transactions.get(step, 0.0) + extra

            # Convert per-step transactions into sparse SimulationCashFlow list.
            transactions: List[SimulationCashFlow] = []
            for step, value in sorted(per_step_transactions.items()):
                if value != 0.0:
                    transactions.append(SimulationCashFlow(step=float(step), value=value))

            result[key] = PortfolioCashflowStreams(
                savings_rates=savings_rates,
                transactions=transactions,
            )

        return result


