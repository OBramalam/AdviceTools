from datetime import date
import datetime
from pydantic import BaseModel, Field

class Income(BaseModel):
    name: str = Field(description="Name of the income source")
    description: str = Field(description="Description of the income source")
    amount: float = Field(
        description=(
            "Cash flow amount. Interpreted as a nominal amount when basis='fixed', "
            "or as a percentage (e.g. 10 = 10%) when basis is percentage-based."
        )
    )
    periodicity: str = Field(
        default='monthly',
        description="Time unit: 'monthly', 'quarterly', 'annually', or 'one_off'",
    )
    frequency: int = Field(
        default=1,
        ge=1,
        description="Number of periods to skip between occurrences (ignored for one_off, e.g. periodicity=monthly, frequency=1 would define monthly incomes)",
    )
    start_age: int = Field(description="Age the income source starts")
    end_age: int = Field(description="Age the income source ends")


class Expense(BaseModel):
    name: str = Field(description="Name of the expense")
    description: str = Field(description="Description of the expense")
    amount: float = Field(
        description=(
            "Cash flow amount. Interpreted as a nominal amount when basis='fixed', "
            "or as a percentage (e.g. 10 = 10%) when basis is percentage-based."
        )
    )
    periodicity: str = Field(
        description="Time unit: 'monthly', 'quarterly', 'annually', or 'one_off'",
    )
    frequency: int = Field(
        description="Number of periods to skip between occurrences (ignored for one_off, e.g. periodicity=monthly, frequency=1 would define monthly expenses)",
    )
    start_age: int = Field(description="Age the expense starts")
    end_age: int = Field(description="Age the expense ends")

class Portfolio(BaseModel):
    """Portfolio structure for extraction (based on PortfolioConfig, without DB ids)."""

    name: str = Field(description="Name of the portfolio")
    initial_portfolio_value: float = Field(
        description="Nominal dollar value of initial wealth allocated to this portfolio",
    )


class ExtractionSchema(BaseModel):
    name: str = Field(description="Name of the client")
    age: float = Field(description="Age of the client")
    retirement_age: float = Field(description="Age the client would like to retire")
    plan_end_age: float = Field(description="Age the client would like to plan to")
    incomes: list[Income] = Field(default_factory=list, description="A list of Income objects defining each source of income described in the text to be extracted. Only extract savings data as income if no incomes and expenses are present in document and savings amount is specifically quoted.")
    expenses: list[Expense] = Field(default_factory=list, description="A list of Expense objects defining each expense described in the text to be extracted.")
    portfolios: list[Portfolio] = Field(default_factory=list, description="A list of Portfolio objects defining each portfolio described in the text to be extracted.")
