"""
Build-Your-Own Robo Advisor  --  FINC 6580 FinTech, Week 3
=============================================================

A deliberately simple goals-based robo advisor.

Pipeline
    1. Gather client information   (questionnaire, Streamlit app, or a ClientProfile object)
    2. Score risk tolerance        (5-question questionnaire -> 1..5 score)
    3. Map goals -> portfolios     (goal-type glide path that de-risks each year, tilted by risk score)
    4. Project outcomes            (Monte Carlo fan chart, sustainable-spending solver)
    5. Display recommendation      (text report + PNG charts; see app.py for the web UI)

Usage
    python robo_advisor.py --demo          # run the three assignment personas
    python robo_advisor.py --interactive   # answer the questionnaire yourself
    streamlit run app.py                   # web interface

Dependencies: numpy, matplotlib (streamlit + plotly for app.py)
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# 0. Capital market assumptions (nominal, annual)
# ----------------------------------------------------------------------------
ASSETS = ["Stocks", "Bonds", "Cash"]
EXP_RETURN = np.array([0.07, 0.04, 0.03])
VOLATILITY = np.array([0.16, 0.06, 0.01])
CORRELATION = np.array(
    [[1.00, 0.10, 0.00],
     [0.10, 1.00, 0.20],
     [0.00, 0.20, 1.00]]
)
COV = np.outer(VOLATILITY, VOLATILITY) * CORRELATION
INFLATION = 0.025
PLAN_TO_AGE = 95          # conservative stand-in for a life-expectancy table
N_SIMULATIONS = 2000
SUCCESS_TARGET = 0.85     # required probability that money lasts to PLAN_TO_AGE
SEED = 6580
DEBT_HURDLE = 0.06        # loans at or above this APR are paid down before investing (a guaranteed return
                          # of 6%+ beats the risky 7% expected from stocks)
MORTGAGE_RATE = 0.065     # 30-year fixed, used for the house affordability check
MORTGAGE_YEARS = 30
DOWN_PAYMENT_PCT = 0.20
HOUSING_COST_PCT = 0.015  # property tax + insurance + maintenance, % of home price per year
HOUSING_RATIO_MAX = 0.28  # housing costs should stay under 28% of gross income

GOAL_KINDS = {
    "house": "Lump sum purchase (house, car, wedding...)",
    "college": "College tuition (lump sum)",
    "retirement": "Retirement income (spend every year)",
    "bequest": "Bequest / legacy (grow and leave)",
}


# ----------------------------------------------------------------------------
# 1. Client data model
# ----------------------------------------------------------------------------
@dataclass
class Goal:
    name: str
    kind: str                      # one of GOAL_KINDS
    years_until: int               # when the money is first needed (0 = spending now)
    target_amount: float = 0.0     # lump sum needed (house, college)
    annual_spending: float = 0.0   # retirement: desired real spending per year
    share_of_savings: float = 1.0  # fraction of annual savings directed to this goal
    share_of_savings_later: float | None = None  # share after the savings-rate change year
    share_of_assets: float = 1.0   # fraction of current assets earmarked for this goal

    @property
    def is_lump_sum(self) -> bool:
        return self.kind in ("house", "college")


LOAN_KINDS = {"credit card": 0.22, "student loan": 0.065, "auto loan": 0.075, "mortgage": 0.055, "other": 0.10}


@dataclass
class Loan:
    name: str
    kind: str                 # one of LOAN_KINDS
    balance: float
    apr: float                # annual interest rate, e.g. 0.22
    min_payment: float        # required payment per YEAR (12 x the monthly minimum)

    @property
    def pay_first(self) -> bool:
        """Should extra savings go here before any investing?"""
        return self.apr >= DEBT_HURDLE


@dataclass
class ClientProfile:
    name: str
    age: int
    current_assets: float
    annual_income: float
    savings_rate_now: float            # fraction of income saved per year today
    savings_rate_future: float         # fraction of income saved after a change
    savings_rate_change_year: int      # year in which the savings rate switches (0 = never)
    income_growth: float               # nominal annual income growth
    goals: list[Goal] = field(default_factory=list)
    risk_answers: list[int] = field(default_factory=list)  # five answers, each 1..5
    other_retirement_income: float = 0.0                   # e.g. Social Security, real $/yr
    loans: list[Loan] = field(default_factory=list)        # savings rate is AFTER required minimum payments
    plan_to_age: int = PLAN_TO_AGE                         # longevity assumption
    success_target: float = SUCCESS_TARGET                 # required probability of not running out

    @property
    def willingness_score(self) -> float:
        """What the questionnaire says the client is willing to bear (1-5)."""
        return float(np.mean(self.risk_answers)) if self.risk_answers else 3.0

    @property
    def capacity_score(self) -> float:
        """What the client's situation can bear (1-5): horizon, job stability, reserves, balance sheet."""
        horizon = max([g.years_until for g in self.goals] + [0])
        h = 5 if horizon >= 20 else 4 if horizon >= 10 else 3 if horizon >= 5 else 2 if horizon >= 2 else 1
        stability = self.risk_answers[3] if len(self.risk_answers) >= 4 else 3
        reserves = self.risk_answers[4] if len(self.risk_answers) >= 5 else 3
        debt = sum(L.balance for L in self.loans)
        nw_ratio = (self.current_assets - debt) / self.annual_income if self.annual_income else 1.0
        b = 5 if nw_ratio >= 3 else 4 if nw_ratio >= 1 else 3 if nw_ratio >= 0 else 1
        return float(np.mean([h, stability, reserves, b]))

    @property
    def risk_score(self) -> float:
        """Effective risk score used for allocation: willingness, capped by capacity plus a small allowance."""
        return float(min(self.willingness_score, self.capacity_score + 0.5))

    @property
    def risk_mismatch(self) -> str | None:
        gap = self.willingness_score - self.capacity_score
        if gap > 1.0:
            return "willingness exceeds capacity"
        if gap < -1.0:
            return "capacity exceeds willingness"
        return None

    @property
    def risk_label(self) -> str:
        s = self.risk_score
        return "Conservative" if s < 2.5 else ("Moderate" if s < 3.75 else "Aggressive")


RISK_QUESTIONS = [
    ("If your portfolio fell 20% in a year, you would...",
     ["sell everything", "sell some", "hold", "buy a little more", "buy a lot more"]),
    ("How much investing experience do you have?",
     ["none", "a little", "some", "quite a bit", "professional"]),
    ("Which matters more to you?",
     ["never losing money", "mostly avoiding losses", "balanced", "mostly growth", "maximum growth"]),
    ("How stable is your income/job?",
     ["very unstable", "somewhat unstable", "average", "stable", "very stable"]),
    ("How long could you cover expenses from savings if income stopped?",
     ["< 1 month", "1-3 months", "3-6 months", "6-12 months", "> 12 months"]),
]


def allocate_remainder(goals: list[Goal]) -> list[str]:
    """Make sure 100% of savings and assets are assigned to some goal.

    Any unassigned share goes to the retirement goal (or the longest-dated goal if
    there is no retirement goal). Shares that sum to more than 100% are scaled down.
    Returns a list of human-readable notes about what was changed.
    """
    notes = []
    if not goals:
        return notes
    sink = next((g for g in goals if g.kind == "retirement"), max(goals, key=lambda g: g.years_until))
    for attr, label in (("share_of_savings", "savings"), ("share_of_assets", "current assets")):
        total = sum(getattr(g, attr) for g in goals)
        if total > 1.0001:
            for g in goals:
                setattr(g, attr, getattr(g, attr) / total)
            notes.append(f"Your {label} shares added up to {total:.0%}; they were scaled down to 100%.")
        elif total < 0.9999:
            setattr(sink, attr, getattr(sink, attr) + (1.0 - total))
            notes.append(f"{1.0 - total:.0%} of your {label} was unassigned; it was added to '{sink.name}'.")
    # the 'later' savings share: everything not claimed by other goals goes to the sink
    others_later = sum((g.share_of_savings_later if g.share_of_savings_later is not None else g.share_of_savings)
                       for g in goals if g is not sink)
    sink.share_of_savings_later = max(0.0, 1.0 - others_later)
    return notes


# ----------------------------------------------------------------------------
# 2. Mapping information -> portfolio (glide path)
# ----------------------------------------------------------------------------
def equity_base(years_remaining: float, kind: str) -> float:
    """Baseline stock weight for a goal with `years_remaining` until the money is needed."""
    if kind == "retirement":
        # 90% stocks 25+ years out, gliding to 45% on the retirement date and thereafter
        return 0.45 + 0.45 * min(years_remaining, 25) / 25
    if kind == "bequest":
        return 0.80
    # lump-sum goals (house, college): 90% far out, gliding to 0% in the last two years
    if years_remaining <= 2:
        return 0.0
    return 0.30 + 0.60 * min(years_remaining - 3, 22) / 22


def recommend_allocation(years_remaining: float, risk_score: float, kind: str) -> np.ndarray:
    """Return weights [stocks, bonds, cash] for one point on the glide path."""
    equity = equity_base(years_remaining, kind)
    # Risk tilt: +/- 15 percentage points of equity between the most conservative and most aggressive client.
    equity += (risk_score - 3.0) / 2.0 * 0.15
    if kind == "retirement" and years_remaining <= 0:
        equity = min(equity, 0.60)      # cap for retirees in the spending phase
        cash = 0.10                     # ~2 years of spending in cash
    elif kind in ("house", "college") and years_remaining <= 2:
        cash = 1.0                      # money needed soon: no market risk
    else:
        cash = 0.05
    equity = float(np.clip(equity, 0.0, 1.0 - cash))
    bonds = 1.0 - equity - cash
    return np.array([equity, bonds, cash])


def allocation_path(goal: Goal, risk_score: float) -> np.ndarray:
    """Weights for each year of the accumulation phase: array (years_until, 3)."""
    return np.array([recommend_allocation(goal.years_until - t, risk_score, goal.kind)
                     for t in range(goal.years_until)])


def portfolio_stats(weights: np.ndarray) -> tuple[float, float]:
    mu = float(weights @ EXP_RETURN)
    sigma = float(np.sqrt(weights @ COV @ weights))
    return mu, sigma


# ----------------------------------------------------------------------------
# 2b. Emergency reserve: cash held back before anything is invested
# ----------------------------------------------------------------------------
def emergency_reserve(client: ClientProfile) -> dict:
    """3 to 6 months of living costs in cash, more when income is less stable. Carved out of current assets."""
    stability = client.risk_answers[3] if len(client.risk_answers) >= 4 else 3
    months = 6 if stability <= 2 else 4 if stability == 3 else 3
    min_payments = sum(L.min_payment for L in client.loans)
    monthly_costs = max(client.annual_income * (1 - client.savings_rate_now) - min_payments, 0) / 12
    if client.annual_income == 0:   # retiree: use planned spending
        spend = max([g.annual_spending for g in client.goals] + [0])
        monthly_costs = spend / 12
    target = months * monthly_costs
    held = min(target, client.current_assets)
    return {"months": months, "monthly_costs": monthly_costs, "target": target, "held": held,
            "shortfall": max(target - client.current_assets, 0.0),
            "investable": max(client.current_assets - held, 0.0)}


# ----------------------------------------------------------------------------
# 3. Debt: pay down or invest?
# ----------------------------------------------------------------------------
def gross_savings(client: ClientProfile, years: int) -> np.ndarray:
    """Nominal savings each year before any accelerated debt paydown."""
    out = np.zeros(years)
    for t in range(years):
        rate = client.savings_rate_now if t < client.savings_rate_change_year else client.savings_rate_future
        out[t] = client.annual_income * (1 + client.income_growth) ** t * rate
    return out


def _run_debt(loans: list[Loan], savings: np.ndarray, accelerate: bool) -> tuple[np.ndarray, np.ndarray, float]:
    """Annual loan balances. Returns (balances[n_loans, years+1], extra_paid[years], total_interest)."""
    years = len(savings)
    bal = np.zeros((len(loans), years + 1))
    bal[:, 0] = [L.balance for L in loans]
    extra = np.zeros(years)
    interest_total = 0.0
    order = sorted(range(len(loans)), key=lambda i: -loans[i].apr)   # avalanche: highest APR first
    for t in range(years):
        pool = savings[t]
        for i, L in enumerate(loans):
            b = bal[i, t]
            if b <= 0:
                continue
            interest = b * L.apr
            interest_total += interest
            bal[i, t + 1] = max(b + interest - L.min_payment, 0.0)
        if accelerate:
            for i in order:
                if loans[i].pay_first and bal[i, t + 1] > 0 and pool > 0:
                    pay = min(pool, bal[i, t + 1])
                    bal[i, t + 1] -= pay
                    pool -= pay
                    extra[t] += pay
    return bal, extra, interest_total


def debt_plan(client: ClientProfile, years: int) -> dict:
    """Decide which loans to attack with savings, and how much savings is left for goals each year."""
    years = max(years, 1)
    savings = gross_savings(client, years)
    if not client.loans:
        return {"loans": [], "available": savings, "savings": savings, "extra": np.zeros(years),
                "balances": np.zeros((0, years + 1)), "payoff_year": [], "interest_plan": 0.0,
                "interest_min_only": 0.0, "debt_free_year": 0, "advice": [], "facts": []}
    bal, extra, interest_plan = _run_debt(client.loans, savings, accelerate=True)
    _, _, interest_min = _run_debt(client.loans, savings, accelerate=False)
    payoff = []
    for i in range(len(client.loans)):
        zero = np.where(bal[i] <= 0)[0]
        payoff.append(int(zero[0]) if len(zero) else None)
    plan = {
        "loans": client.loans, "savings": savings, "available": savings - extra, "extra": extra, "balances": bal,
        "payoff_year": payoff, "interest_plan": interest_plan, "interest_min_only": interest_min,
        "debt_free_year": max((y for y in payoff if y is not None), default=None) if all(y is not None for y in payoff) else None,
        "advice": [], "facts": [],
    }
    total = sum(L.balance for L in client.loans)
    plan["facts"].append(f"Total debt {fmt(total)} against {fmt(client.current_assets)} of assets: net worth {fmt(client.current_assets - total)}.")
    for L, py in zip(client.loans, payoff):
        when = f"paid off in year {py}" if py is not None else f"not paid off within {years} years"
        if L.pay_first:
            plan["advice"].append(
                f"{L.name} ({L.apr:.1%} APR): paying this down is a guaranteed {L.apr:.1%} return, better than the "
                f"{EXP_RETURN[0]:.0%} expected from stocks. Direct savings here before investing; {when}.")
        else:
            plan["advice"].append(
                f"{L.name} ({L.apr:.1%} APR): below the {DEBT_HURDLE:.0%} hurdle. Pay the minimum and invest the rest; {when}.")
    saved = interest_min - interest_plan
    if saved > 0:
        plan["facts"].append(f"Attacking high-rate debt first saves about {fmt(saved)} of interest versus minimum payments only.")
    diverted = extra.sum()
    if diverted > 0:
        plan["facts"].append(f"{fmt(diverted)} of savings is diverted to debt paydown before it can go to your goals.")
    return plan


# ----------------------------------------------------------------------------
# 4. Projections
# ----------------------------------------------------------------------------
def contribution_schedule(client: ClientProfile, goal: Goal, years: int, available: np.ndarray | None = None) -> np.ndarray:
    """Nominal contributions to this goal in each future year (after any debt paydown)."""
    if available is None:
        available = debt_plan(client, years)["available"]
    contrib = np.zeros(years)
    for t in range(years):
        early = t < client.savings_rate_change_year
        share = goal.share_of_savings if (early or goal.share_of_savings_later is None) else goal.share_of_savings_later
        contrib[t] = available[t] * share
    return contrib


def simulate_accumulation(start: float, contributions: np.ndarray, weight_path: np.ndarray,
                          n_sims: int = N_SIMULATIONS, seed: int = SEED) -> np.ndarray:
    """Monte Carlo wealth paths while saving, with the allocation changing each year."""
    rng = np.random.default_rng(seed)
    years = len(contributions)
    paths = np.empty((n_sims, years + 1))
    paths[:, 0] = start
    for t in range(years):
        mu, sigma = portfolio_stats(weight_path[t])
        shocks = rng.normal(mu - 0.5 * sigma**2, sigma, size=n_sims)   # log-normal annual returns
        paths[:, t + 1] = paths[:, t] * np.exp(shocks) + contributions[t]
    return paths


def simulate_drawdown(start: float, annual_spending_real: float, years: int, weights: np.ndarray,
                      other_income_real: float = 0.0, n_sims: int = N_SIMULATIONS, seed: int = SEED) -> np.ndarray:
    """Monte Carlo wealth paths while spending (spending grows with inflation)."""
    rng = np.random.default_rng(seed)
    mu, sigma = portfolio_stats(weights)
    shocks = rng.normal(mu - 0.5 * sigma**2, sigma, size=(n_sims, years))
    paths = np.empty((n_sims, years + 1))
    paths[:, 0] = start
    for t in range(years):
        withdrawal = max(annual_spending_real - other_income_real, 0.0) * (1 + INFLATION) ** t
        paths[:, t + 1] = np.maximum(paths[:, t] * np.exp(shocks[:, t]) - withdrawal, 0.0)
    return paths


def sustainable_spending(start: float, years: int, weights: np.ndarray, other_income_real: float = 0.0,
                         target: float = SUCCESS_TARGET) -> float:
    """Largest real annual portfolio withdrawal with >= target probability of lasting `years` (bisection)."""
    lo, hi = 0.0, start
    for _ in range(30):
        mid = (lo + hi) / 2
        paths = simulate_drawdown(start, mid, years, weights, 0.0, n_sims=800)
        if np.mean(paths[:, -1] > 0) >= target:
            lo = mid
        else:
            hi = mid
    return lo


# ----------------------------------------------------------------------------
# 4. Analysis of one goal (structured result used by both the CLI and the web app)
# ----------------------------------------------------------------------------
def fmt(x: float) -> str:
    return f"${x:,.0f}"


def slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")[:40]


def mortgage_check(client: ClientProfile, goal: Goal, p50: float) -> tuple[list[str], list[str]]:
    """Can the client afford the home that the down payment implies?"""
    price = goal.target_amount / DOWN_PAYMENT_PCT
    loan = price * (1 - DOWN_PAYMENT_PCT)
    r = MORTGAGE_RATE
    annual_payment = loan * r / (1 - (1 + r) ** -MORTGAGE_YEARS)
    housing = annual_payment + price * HOUSING_COST_PCT
    income_then = client.annual_income * (1 + client.income_growth) ** goal.years_until
    ratio = housing / income_then if income_then else float("inf")
    facts = [f"A {fmt(goal.target_amount)} down payment ({DOWN_PAYMENT_PCT:.0%}) implies a {fmt(price)} home and a "
             f"{fmt(loan)} mortgage: about {fmt(annual_payment / 12)}/month at {MORTGAGE_RATE:.1%}, "
             f"{fmt(housing / 12)}/month with taxes and upkeep = {ratio:.0%} of your projected income then."]
    advice = []
    if ratio > HOUSING_RATIO_MAX:
        max_price = HOUSING_RATIO_MAX * income_then / (r / (1 - (1 + r) ** -MORTGAGE_YEARS) * (1 - DOWN_PAYMENT_PCT) + HOUSING_COST_PCT)
        advice.append(f"That is above the {HOUSING_RATIO_MAX:.0%} affordability guideline. A home around {fmt(max_price)} "
                      f"(down payment {fmt(max_price * DOWN_PAYMENT_PCT)}) would fit your income.")
    else:
        advice.append(f"Housing cost is within the {HOUSING_RATIO_MAX:.0%} guideline, so the mortgage looks affordable.")
    return facts, advice


def analyze_goal(client: ClientProfile, goal: Goal, available: np.ndarray | None = None,
                 investable: float | None = None) -> dict:
    r = {"goal": goal, "advice": [], "facts": []}
    base_assets = client.current_assets if investable is None else investable
    start = base_assets * goal.share_of_assets
    r["start"] = start

    # ---- Accumulation phase --------------------------------------------
    if goal.years_until > 0:
        wpath = allocation_path(goal, client.risk_score)
        avail = available[:goal.years_until] if available is not None else None
        contrib = contribution_schedule(client, goal, goal.years_until, avail)
        paths = simulate_accumulation(start, contrib, wpath)
        final = paths[:, -1]
        p10, p50, p90 = np.percentile(final, [10, 50, 90])
        r.update(
            phase="accumulation", weights_now=wpath[0], weight_path=wpath,
            x=np.arange(goal.years_until + 1), x_label="Years from now",
            band=(np.percentile(paths, 10, axis=0), np.percentile(paths, 50, axis=0), np.percentile(paths, 90, axis=0)),
            band_inner=(np.percentile(paths, 25, axis=0), np.percentile(paths, 75, axis=0)),
            contributions=contrib, p10=p10, p50=p50, p90=p90,
            p50_real=p50 / (1 + INFLATION) ** goal.years_until,
        )
        r["mu"], r["sigma"] = portfolio_stats(wpath[0])
        r["facts"].append(f"Starting balance {fmt(start)}; contributions total {fmt(contrib.sum())} over {goal.years_until} years.")
        r["facts"].append(f"Projected balance at goal date: median {fmt(p50)} "
                          f"(10th pct {fmt(p10)}, 90th pct {fmt(p90)}), i.e. {fmt(r['p50_real'])} in today's dollars.")

        r.setdefault("lifetime_x", np.arange(goal.years_until + 1) + client.age)
        r.setdefault("lifetime_median", np.percentile(paths, 50, axis=0))
        if goal.is_lump_sum:
            prob = float(np.mean(final >= goal.target_amount)) if goal.target_amount > 0 else 1.0
            r["target_prob"] = prob
            r["facts"].append(f"Target {fmt(goal.target_amount)}: probability of reaching it = {prob:.0%}.")
            if prob < 0.8:
                extra = max((goal.target_amount - p10) / goal.years_until, 0)
                r["advice"].append(f"Save about {fmt(extra)} more per year toward this goal, or push the date out.")
            else:
                r["advice"].append("On track. Keep this goal's money on the glide path above; it moves to cash in the last two years.")
            if goal.kind == "house" and goal.target_amount > 0:
                mf, ma = mortgage_check(client, goal, p50)
                r["facts"] += mf
                r["advice"] += ma

        elif goal.kind == "retirement":
            years_spend = max(client.plan_to_age - client.age - goal.years_until, 1)
            w_ret = recommend_allocation(0, client.risk_score, "retirement")
            sust = sustainable_spending(p50, years_spend, w_ret, target=client.success_target)
            sust_real = sust / (1 + INFLATION) ** goal.years_until
            other = client.other_retirement_income
            r.update(weights_retirement=w_ret, years_spend=years_spend, sustainable=sust, sustainable_real=sust_real,
                     total_income_real=sust_real + other)
            # lifetime path: median accumulation, then median drawdown at the desired spending
            need_nominal = max(goal.annual_spending - other, 0) * (1 + INFLATION) ** goal.years_until
            dd = simulate_drawdown(p50, need_nominal, years_spend, w_ret, 0.0, n_sims=600)
            r["lifetime_x"] = np.arange(goal.years_until + years_spend + 1) + client.age
            r["lifetime_median"] = np.r_[np.percentile(paths, 50, axis=0), np.percentile(dd, 50, axis=0)[1:]]
            r["lifetime_low"] = np.r_[np.percentile(paths, 10, axis=0), np.percentile(dd, 10, axis=0)[1:]]
            r["lifetime_high"] = np.r_[np.percentile(paths, 90, axis=0), np.percentile(dd, 90, axis=0)[1:]]
            r["facts"].append(f"At retirement the portfolio shifts to " +
                              ", ".join(f"{a} {w:.0%}" for a, w in zip(ASSETS, w_ret)) + ".")
            r["facts"].append(f"The median balance supports about {fmt(sust_real)}/yr in today's dollars for {years_spend} years "
                              f"with {client.success_target:.0%} confidence, plus {fmt(other)}/yr of other income "
                              f"= {fmt(sust_real + other)}/yr total.")
            if sust_real + other >= goal.annual_spending:
                r["advice"].append(f"Retirement goal of {fmt(goal.annual_spending)}/yr looks fundable.")
            else:
                gap = goal.annual_spending - sust_real - other
                r["advice"].append(f"Expected shortfall of {fmt(gap)}/yr (today's dollars) versus the {fmt(goal.annual_spending)}/yr goal. "
                                   f"Save more, retire later, or plan to spend less.")
        else:  # bequest
            r["advice"].append("Growth portfolio held for heirs; no spending is planned from it.")

    # ---- Drawdown phase (already retired) ------------------------------
    else:
        w = recommend_allocation(0, client.risk_score, goal.kind)
        years_spend = max(client.plan_to_age - client.age, 1)
        other = client.other_retirement_income
        paths = simulate_drawdown(start, goal.annual_spending, years_spend, w, other)
        success = float(np.mean(paths[:, -1] > 0))
        sust = sustainable_spending(start, years_spend, w, target=client.success_target)
        withdrawal = max(goal.annual_spending - other, 0)
        r.update(
            phase="drawdown", weights_now=w, weight_path=np.tile(w, (years_spend, 1)),
            x=np.arange(years_spend + 1) + client.age, x_label="Age",
            band=(np.percentile(paths, 10, axis=0), np.percentile(paths, 50, axis=0), np.percentile(paths, 90, axis=0)),
            band_inner=(np.percentile(paths, 25, axis=0), np.percentile(paths, 75, axis=0)),
            success=success, sustainable_real=sust + other, years_spend=years_spend,
            withdrawal_rate=withdrawal / start if start else 0.0,
            median_end=float(np.percentile(paths[:, -1], 50)),
        )
        r["mu"], r["sigma"] = portfolio_stats(w)
        r["facts"].append(f"Spending {fmt(goal.annual_spending)}/yr minus {fmt(other)} other income = "
                          f"{fmt(withdrawal)}/yr from the portfolio ({r['withdrawal_rate']:.1%} initial withdrawal rate).")
        r["lifetime_x"] = r["x"]; r["lifetime_median"] = r["band"][1]; r["lifetime_low"] = r["band"][0]; r["lifetime_high"] = r["band"][2]
        r["facts"].append(f"Probability the money lasts {years_spend} years (to age {client.plan_to_age}): {success:.0%}.")
        r["facts"].append(f"Maximum sustainable spending at {client.success_target:.0%} confidence: {fmt(sust + other)}/yr (today's dollars, incl. other income).")
        r["facts"].append(f"Median balance left at age {client.plan_to_age}: {fmt(r['median_end'])} (potential bequest).")
        if success >= client.success_target:
            r["advice"].append("Spending plan is sustainable. Keep about two years of spending in cash and rebalance annually.")
        else:
            r["advice"].append(f"Trim spending toward {fmt(sust + other)}/yr, or accept a higher chance of running short.")
    return r


def _funded(client: ClientProfile, goal: Goal, debt_available: np.ndarray, investable: float) -> bool:
    r = analyze_goal(client, goal, debt_available, investable)
    if goal.kind == "retirement" and r["phase"] == "accumulation":
        return r["total_income_real"] >= goal.annual_spending
    if goal.is_lump_sum:
        return r.get("target_prob", 1.0) >= 0.8
    return True


def what_it_takes(client: ClientProfile, goal: Goal, investable: float) -> dict:
    """For an under-funded goal: the savings rate, or the later date, that would fund it."""
    from copy import deepcopy
    out = {}
    horizon = max([g.years_until for g in client.goals] + [client.plan_to_age - client.age, 1])
    # (a) savings rate: scale both current and future rates until funded (cap at 60%)
    lo, hi = client.savings_rate_now, 0.60
    if client.annual_income > 0 and lo < hi:
        c = deepcopy(client)
        def ok(rate):
            c.savings_rate_now = rate
            c.savings_rate_future = max(client.savings_rate_future, rate)
            return _funded(c, goal, debt_plan(c, horizon)["available"], investable)
        if ok(hi):
            for _ in range(8):
                mid = (lo + hi) / 2
                if ok(mid):
                    hi = mid
                else:
                    lo = mid
            out["savings_rate"] = hi
    # (b) later date: push the goal out year by year (cap +10 years)
    c = deepcopy(client)
    g = next(x for x in c.goals if x.name == goal.name)
    for extra in range(1, 11):
        g.years_until = goal.years_until + extra
        if _funded(c, g, debt_plan(c, horizon + extra)["available"], investable):
            out["delay_years"] = extra
            break
    return out


def analyze_client(client: ClientProfile) -> tuple[list[dict], list[str], dict, dict]:
    """Returns (per-goal results, allocation notes, debt plan, emergency reserve)."""
    notes = allocate_remainder(client.goals)
    horizon = max([g.years_until for g in client.goals] + [client.plan_to_age - client.age, 1])
    debt = debt_plan(client, horizon)
    reserve = emergency_reserve(client)
    results = [analyze_goal(client, g, debt["available"], reserve["investable"]) for g in client.goals]
    for r in results:
        g = r["goal"]
        short = (g.kind == "retirement" and r["phase"] == "accumulation" and r["total_income_real"] < g.annual_spending) or \
                (g.is_lump_sum and r.get("target_prob", 1.0) < 0.8)
        if short and g.years_until > 0:
            fix = what_it_takes(client, g, reserve["investable"])
            r["what_it_takes"] = fix
            parts = []
            if "savings_rate" in fix:
                parts.append(f"raise your savings rate to about {fix['savings_rate']:.0%}")
            if "delay_years" in fix:
                parts.append(f"move the date out {fix['delay_years']} year{'s' if fix['delay_years'] > 1 else ''}"
                             + (f" (retire at {client.age + g.years_until + fix['delay_years']})" if g.kind == "retirement" else ""))
            if parts:
                r["advice"].append("What it takes: " + ", or ".join(parts) + ".")
            elif g.kind == "retirement":
                r["advice"].append(f"What it takes: no single change closes this gap. Combine a higher savings rate with a later "
                                   f"retirement, or plan on about {fmt(r['total_income_real'])}/yr of spending.")
            else:
                r["advice"].append("What it takes: no single change closes this gap. Lower the target or combine more saving with a later date.")
    if client.risk_mismatch:
        notes.append(f"Risk check: your {client.risk_mismatch} (willingness {client.willingness_score:.1f}, capacity {client.capacity_score:.1f}). "
                     f"Allocations use an effective score of {client.risk_score:.1f}.")
    if reserve["target"] > 0:
        notes.append(f"Emergency reserve: {reserve['months']} months of living costs = {fmt(reserve['target'])} held in cash before investing"
                     + (f"; you are {fmt(reserve['shortfall'])} short of it." if reserve["shortfall"] > 0 else "."))
    return results, notes, debt, reserve


# ----------------------------------------------------------------------------
# 5. Text report + PNG charts (command-line output)
# ----------------------------------------------------------------------------
def format_report(client: ClientProfile, results: list[dict], notes: list[str], debt: dict) -> str:
    """Plain-text recommendation (used by the CLI and the app's download button)."""
    lines = []
    p = lines.append
    p("=" * 78)
    p(f"ROBO ADVISOR RECOMMENDATION FOR: {client.name}")
    p("=" * 78)
    p(f"Age {client.age} | Assets {fmt(client.current_assets)} | Income {fmt(client.annual_income)} | "
      f"Saving {client.savings_rate_now:.0%} now, {client.savings_rate_future:.0%} later")
    p(f"Risk: willingness {client.willingness_score:.1f}, capacity {client.capacity_score:.1f}, effective {client.risk_score:.1f} / 5  ->  {client.risk_label}")
    p(f"Planning horizon: to age {client.plan_to_age} at {client.success_target:.0%} confidence. Inflation assumed {INFLATION:.1%}.")
    for n in notes:
        p(f"NOTE: {n}")
    p("")
    if debt["loans"]:
        p("-" * 78)
        p("DEBT: pay down or invest?")
        p("-" * 78)
        for L in debt["loans"]:
            p(f"{L.name:<22} {L.kind:<13} balance {fmt(L.balance):>12}  APR {L.apr:.1%}  min {fmt(L.min_payment)}/yr")
        for f_ in debt["facts"]:
            p(f_)
        for a in debt["advice"]:
            p(f"  ADVICE: {a}")
        p("")
    for gi, r in enumerate(results):
        goal = r["goal"]
        p("-" * 78)
        p(f"GOAL {gi + 1}: {goal.name} [{goal.kind}]  (money needed in {goal.years_until} years)")
        p("-" * 78)
        p("Recommended portfolio today:  " + "  ".join(f"{a} {w:.0%}" for a, w in zip(ASSETS, r["weights_now"])))
        p(f"Expected return {r['mu']:.1%} / yr, volatility {r['sigma']:.1%} / yr")
        for f_ in r["facts"]:
            p(f_)
        for a in r["advice"]:
            p(f"  ADVICE: {a}")
        p("")
    return "\n".join(lines)


def advise(client: ClientProfile, outdir: str = "output") -> str:
    """Run the analysis, save a PNG chart sheet and a text report, and return the report."""
    os.makedirs(outdir, exist_ok=True)
    results, notes, debt, reserve = analyze_client(client)
    report = format_report(client, results, notes, debt)

    n_rows = len(results) + (1 if debt["loans"] else 0)
    fig, axes = plt.subplots(n_rows, 3, figsize=(16, 4.2 * n_rows), squeeze=False)

    if debt["loans"]:
        row = len(results)
        axd = axes[row, 0]
        yrs = np.arange(debt["balances"].shape[1])
        show = min(len(yrs), 31)
        for i, L in enumerate(debt["loans"]):
            axd.plot(yrs[:show], debt["balances"][i, :show], lw=2, label=f"{L.name} ({L.apr:.0%})")
        axd.set_title("Loan balances"); axd.set_xlabel("Years from now")
        axd.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1e3:,.0f}K")); axd.legend()
        axs = axes[row, 1]
        ys = np.arange(show - 1)
        axs.bar(ys, debt["extra"][:show - 1], label="To debt paydown", color="#d62728")
        axs.bar(ys, debt["available"][:show - 1], bottom=debt["extra"][:show - 1], label="To goals", color="#1f77b4")
        axs.set_title("Where each year's savings go"); axs.set_xlabel("Years from now")
        axs.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1e3:,.0f}K")); axs.legend()
        axes[row, 2].axis("off")

    for gi, r in enumerate(results):
        goal = r["goal"]
        axp = axes[gi, 0]
        w = r["weights_now"]
        nz = w > 0.005
        axp.pie(w[nz], labels=[a for a, k in zip(ASSETS, nz) if k], autopct="%1.0f%%", startangle=90,
                colors=[c for c, k in zip(["#1f77b4", "#2ca02c", "#bcbd22"], nz) if k])
        axp.set_title(f"{goal.name}: allocation today")
        axg = axes[gi, 1]
        wp = r["weight_path"]
        xs = r["x"][:-1]
        axg.stackplot(xs, wp[:, 0], wp[:, 1], wp[:, 2], labels=ASSETS, colors=["#1f77b4", "#2ca02c", "#bcbd22"], alpha=0.85)
        axg.set_ylim(0, 1); axg.set_xlabel(r["x_label"]); axg.set_title(f"{goal.name}: glide path")
        axg.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); axg.legend(loc="lower left")
        ax = axes[gi, 2]
        lo, mid, hi = r["band"]
        ax.fill_between(r["x"], lo, hi, alpha=0.25, label="10th-90th percentile")
        ax.plot(r["x"], mid, lw=2, label="Median")
        if goal.is_lump_sum and goal.target_amount > 0:
            ax.axhline(goal.target_amount, ls="--", color="gray", label="Target")
        ax.set_title(f"{goal.name}: projected balance")
        ax.set_xlabel(r["x_label"]); ax.set_ylabel("Nominal $")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1e3:,.0f}K"))
        ax.legend()

    fig.suptitle(f"{client.name} - {client.risk_label} investor", fontsize=14)
    fig.tight_layout()
    chart = os.path.join(outdir, f"{slug(client.name)}_charts.png")
    fig.savefig(chart, dpi=110)
    plt.close(fig)
    report += f"\nCharts saved to {chart}"
    with open(os.path.join(outdir, f"{slug(client.name)}_report.txt"), "w") as f:
        f.write(report)
    return report


# ----------------------------------------------------------------------------
# 6. Interactive questionnaire
# ----------------------------------------------------------------------------
def ask(prompt: str, cast=float, default=None):
    """Prompt until the answer parses. Accepts '$1,200', '20,000', '15%' etc."""
    while True:
        raw = input(f"{prompt}{f' [{default}]' if default is not None else ''}: ").strip()
        if not raw:
            return default
        if cast is str:
            return raw
        cleaned = raw.replace(",", "").replace("$", "").replace("_", "").strip()
        is_pct = cleaned.endswith("%")
        cleaned = cleaned.rstrip("%").strip()
        try:
            value = float(cleaned)
        except ValueError:
            print("   Please enter a number (commas and $ are fine).")
            continue
        if is_pct:
            value /= 100
        return cast(value) if cast is not float else value


def rate(x) -> float:
    """Cast for rates: '20' or '20%' -> 0.20, '0.2' -> 0.2."""
    x = float(x)
    return x / 100 if x > 1 else x


def interactive_profile() -> ClientProfile:
    print("\nWelcome to the FINC6580 robo advisor. Let's get to know you.\n")
    name = ask("Your name", str, "Client")
    age = ask("Your age", int, 35)
    assets = ask("Current investable financial assets ($)", float, 50000)
    income = ask("Expected annual income ($)", float, 80000)
    sr_now = ask("Share of income you save now (e.g. 0.15 or 15%)", rate, 0.15)
    sr_year = ask("In how many years will your savings rate change? (0 if never)", int, 0)
    sr_fut = ask("Share of income you will save after that change", rate, sr_now) if sr_year else sr_now
    growth = ask("Expected annual income growth (e.g. 0.03 or 3%)", rate, 0.03)
    other = ask("Other retirement income such as Social Security ($/yr, today's $)", float, 0.0)

    goals = []
    kinds = list(GOAL_KINDS)
    print("\nNow your goals. Any savings or assets you do not assign go to retirement automatically.")
    while True:
        print("  Goal types: " + "  ".join(f"{i}. {k}" for i, k in enumerate(kinds, 1)) + "   (blank = done)")
        choice = ask("Goal type number", str, "")
        if not choice:
            break
        try:
            kind = kinds[int(choice) - 1]
        except (ValueError, IndexError):
            print("   Please enter 1-4.")
            continue
        gname = ask("  Goal name", str, kind.title())
        if kind == "retirement":
            retire_age = ask("  Age you plan to retire (enter your current age if already retired)", int, 65)
            yrs = max(retire_age - age, 0)
            spend = ask("  Annual spending you want in retirement ($/yr, today's $)", float, 60000)
            goals.append(Goal(gname, kind, yrs, 0.0, spend, 0.0, None, 0.0))   # shares filled by remainder
        elif kind == "bequest":
            goals.append(Goal(gname, kind, max(PLAN_TO_AGE - age, 1), 0.0, 0.0,
                              ask("  Share of your savings for this goal (0-1)", float, 0.1), None,
                              ask("  Share of current assets for this goal (0-1)", float, 0.1)))
        else:
            yrs = ask("  Years until you need the money", int, 5)
            target = ask("  Lump sum needed ($)", float, 50000)
            share_s = ask("  Share of your savings for this goal (0-1)", float, 0.5)
            share_a = ask("  Share of current assets for this goal (0-1)", float, 0.5)
            goals.append(Goal(gname, kind, yrs, target, 0.0, share_s, 0.0, share_a))  # after the date, savings go elsewhere
    if not goals:
        goals.append(Goal("Retirement", "retirement", max(65 - age, 0), 0.0, 60000, 0.0, None, 0.0))
        print("No goals entered; assuming retirement at 65 on $60,000/yr.")

    loans = []
    lkinds = list(LOAN_KINDS)
    print("\nNow any loans. Your savings rate should be what is left AFTER required minimum payments.")
    while True:
        print("  Loan types: " + "  ".join(f"{i}. {k}" for i, k in enumerate(lkinds, 1)) + "   (blank = done)")
        choice = ask("Loan type number", str, "")
        if not choice:
            break
        try:
            lkind = lkinds[int(choice) - 1]
        except (ValueError, IndexError):
            print("   Please enter 1-5.")
            continue
        lname = ask("  Loan name", str, lkind.title())
        bal = ask("  Current balance ($)", float, 10000)
        apr = ask("  Interest rate (APR, e.g. 6.5%)", rate, LOAN_KINDS[lkind])
        monthly = ask("  Required minimum payment per month ($)", float, round(bal * 0.02))
        loans.append(Loan(lname, lkind, bal, apr, monthly * 12))

    print("\nRisk tolerance questionnaire (answer 1-5):")
    answers = []
    for q, opts in RISK_QUESTIONS:
        print(f"  {q}")
        for i, o in enumerate(opts, 1):
            print(f"     {i}. {o}")
        answers.append(int(np.clip(ask("  Your answer", int, 3), 1, 5)))

    return ClientProfile(name, age, assets, income, sr_now, sr_fut, sr_year, growth, goals, answers, other, loans)


# ----------------------------------------------------------------------------
# 6b. Course-topic helpers: portfolio risk, 5 Cs of credit, KYC
# ----------------------------------------------------------------------------
def frontier(cash: float = 0.05, steps: int = 20) -> list[tuple[float, float, float]]:
    """(stock weight, expected return, volatility) along the stock/bond mix. Used for the risk-return chart."""
    out = []
    for i in range(steps + 1):
        eq = (1 - cash) * i / steps
        w = np.array([eq, 1 - cash - eq, cash])
        mu, sigma = portfolio_stats(w)
        out.append((eq, mu, sigma))
    return out


def credit_health(client: ClientProfile) -> dict:
    """A simple '5 Cs of credit' style scorecard a lender (or robo) would compute from the intake data."""
    total_debt = sum(L.balance for L in client.loans)
    min_payments = sum(L.min_payment for L in client.loans)
    income = client.annual_income
    dti = min_payments / income if income else (1.0 if total_debt else 0.0)
    net_worth = client.current_assets - total_debt
    emergency = client.risk_answers[4] if len(client.risk_answers) >= 5 else 3     # months of expenses proxy
    stability = client.risk_answers[3] if len(client.risk_answers) >= 4 else 3
    items = [
        ("Capacity", "Debt payments / income", f"{dti:.0%}", 5 if dti < 0.10 else 4 if dti < 0.20 else 3 if dti < 0.36 else 1,
         "Lenders look for total debt service under 36% of income."),
        ("Capital", "Net worth", fmt(net_worth), 5 if net_worth > 2 * income else 4 if net_worth > income else 3 if net_worth > 0 else 1,
         "Assets minus liabilities: your own stake in the plan."),
        ("Character", "Savings habit", f"{client.savings_rate_now:.0%} of income",
         5 if client.savings_rate_now >= 0.20 else 4 if client.savings_rate_now >= 0.15 else 3 if client.savings_rate_now >= 0.10 else 2,
         "A consistent savings rate is the strongest signal of repayment discipline."),
        ("Collateral", "Liquid assets", fmt(client.current_assets), 5 if client.current_assets > income else 3 if client.current_assets > 0.25 * income else 2,
         "Assets that could be pledged or sold. Real estate is not yet included."),
        ("Conditions", "Job stability, emergency fund", f"{stability}/5, {emergency}/5", int(round((stability + emergency) / 2)),
         "Job stability and emergency reserves from your risk profile."),
    ]
    score = sum(i[3] for i in items) / (5 * len(items))
    return {"items": items, "score": score, "dti": dti, "net_worth": net_worth, "total_debt": total_debt,
            "grade": "A" if score >= 0.85 else "B" if score >= 0.7 else "C" if score >= 0.55 else "D"}


def kyc_check(name: str, age: int, attested: bool) -> dict:
    """Simulated AML/KYC onboarding gate. A real robo would call an identity-verification and sanctions-screening API."""
    checks = [
        ("Identity provided", bool(name and name.strip() and name.strip().lower() != "client")),
        ("Age 18 or over", age >= 18),
        ("Customer attestation", attested),
        ("Sanctions / PEP screening (simulated)", True),
    ]
    return {"checks": checks, "passed": all(ok for _, ok in checks)}


# ----------------------------------------------------------------------------
# 7. Assignment personas
# ----------------------------------------------------------------------------
def demo_profiles() -> list[ClientProfile]:
    a = ClientProfile(
        name="Client A: Early-career saver, 30", age=30, current_assets=40_000, annual_income=90_000,
        savings_rate_now=0.20, savings_rate_future=0.15, savings_rate_change_year=2, income_growth=0.03,
        goals=[
            # 70% of savings and 75% of assets go to the house until it is bought in year 2; then 0%.
            Goal("House down payment", "house", years_until=2, target_amount=60_000,
                 share_of_savings=0.70, share_of_savings_later=0.0, share_of_assets=0.75),
            # Retirement gets the remainder: 30% of savings now, 100% after the house.
            Goal("Retirement at 65", "retirement", years_until=35, annual_spending=70_000,
                 share_of_savings=0.30, share_of_assets=0.25),
        ],
        risk_answers=[4, 2, 4, 4, 3], other_retirement_income=25_000,
        loans=[
            Loan("Credit card", "credit card", balance=4_000, apr=0.22, min_payment=1_200),
            Loan("Student loan", "student loan", balance=30_000, apr=0.055, min_payment=4_200),
        ],
    )
    b = ClientProfile(
        name="Client B: Pre-retiree, 55", age=55, current_assets=200_000, annual_income=110_000,
        savings_rate_now=0.15, savings_rate_future=0.15, savings_rate_change_year=0, income_growth=0.02,
        goals=[Goal("Retirement at 65", "retirement", years_until=10, annual_spending=70_000)],
        risk_answers=[3, 3, 3, 4, 3], other_retirement_income=30_000,
        loans=[Loan("Mortgage", "mortgage", balance=150_000, apr=0.035, min_payment=14_400)],
    )
    c = ClientProfile(
        name="Client C: Retiree, 70", age=70, current_assets=2_000_000, annual_income=0,
        savings_rate_now=0.0, savings_rate_future=0.0, savings_rate_change_year=0, income_growth=0.0,
        goals=[Goal("Retirement spending", "retirement", years_until=0, annual_spending=120_000)],
        risk_answers=[3, 4, 2, 5, 5], other_retirement_income=40_000,
    )
    return [a, b, c]


def main():
    parser = argparse.ArgumentParser(description="FINC6580 build-your-own robo advisor")
    parser.add_argument("--demo", action="store_true", help="run the three assignment personas")
    parser.add_argument("--interactive", action="store_true", help="answer the questionnaire")
    parser.add_argument("--outdir", default="output")
    args = parser.parse_args()

    if args.interactive:
        print(advise(interactive_profile(), args.outdir))
    else:
        for client in demo_profiles():
            print(advise(client, args.outdir))
            print()


if __name__ == "__main__":
    main()
