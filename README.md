# Build Your Own Robo Advisor
**FINC 6580 FinTech, Fall 2026, Week 3** | Jose Ochoa Tello | Georgetown MSBA

## What's in this folder

| File | Purpose |
|---|---|
| `robo_advisor.py` | The robo engine and command-line questionnaire (Python 3, numpy, matplotlib) |
| `app.py` | "Ascend" web app: **Sample Clients**, **Plan Builder** and **Methodology** pages |
| `ui.py` | Product theme (Inter font, dark navy/teal), chart components and dashboard layout |
| `.streamlit/config.toml` | Theme and minimal toolbar |
| `AI_PROMPTS.md` | The AI prompts used to build it |
| `output/*_report.txt` | Text recommendation for each persona |
| `output/*_charts.png` | Allocation pie + Monte Carlo fan chart for each persona |

Run it:

```bash
python robo_advisor.py --demo          # the three assignment personas
python robo_advisor.py --interactive   # answer the questionnaire yourself
streamlit run app.py                   # web app (three pages, see below)
```

## The web app: Ascend

The app is presented as a product rather than a class exercise, the way a robo
adviser would be shown to a customer or an investor.

- **Sample Clients**: the three assignment clients (early-career saver, pre-retiree,
  retiree) with an at-a-glance comparison and a full dashboard each.
- **Plan Builder**: the customer flow. Verify identity (simulated KYC and sanctions
  screening), connect accounts (manual entry standing in for account linking),
  goals, loans, risk profile, then a plan that updates live and can be downloaded.
- **Methodology**: every rule that maps an input to a recommendation, the capital
  market assumptions, why the success threshold is 85%, and the product roadmap.

Each dashboard includes a plan score, KPI tiles, identity-verification status, a
lifetime wealth trajectory (every goal's median balance by age, debt below the line,
net worth on top), a balance sheet, a year-one cash-flow diagram (income to living
costs, loan minimums, debt paydown and each goal), a credit-health grade built on
the five factors a lender weighs, a debt strategy, goal cards with a health gauge,
allocation donut, glide path and two-band projection fan chart, and a risk and
return view of where each goal's portfolio sits.

### Planning logic, in order

1. **Risk capacity vs willingness.** The questionnaire measures willingness. A
   capacity score is computed from horizon, job stability, emergency reserves and
   net worth relative to income. Allocations use the lower of the two (plus a small
   allowance) and the dashboard flags a mismatch.
2. **Emergency reserve.** Three to six months of living costs (more when income is
   less stable) is held in cash before anything is invested.
3. **Debt.** Loans at or above a 6% APR are paid down highest-rate-first with
   savings before investing; cheaper loans get minimum payments.
4. **Goals.** Each goal gets a glide path that de-risks every year, Monte Carlo
   projections (2,000 paths) and, for retirement, the largest inflation-indexed
   withdrawal that survives to the planning age at the required confidence. The
   planning age (85 to 100) and confidence (75 to 95%) are user settings.
5. **What it takes.** For any under-funded goal the engine solves for the savings
   rate, or the later date, that would fund it, and says so when no single change is
   enough.

Where course material shows up without being labelled as such: AML/KYC onboarding,
open banking (account linking), the accounting identity (balance sheet), the 5 Cs of
credit (credit health), lending and credit (debt strategy), portfolio risk (risk and
return chart), and model explainability (Methodology page).

## How the robo works

1. **Gather information.** Age, current financial assets, expected income and
   income growth, savings rate now and in the future, other retirement income
   (Social Security), a list of typed goals and a 5-question risk-tolerance
   quiz (reaction to a 20% loss, experience, loss-vs-growth preference, job
   stability, emergency fund). The quiz averages to a score of 1 to 5.
   Goals are one of four types, and the robo asks only the relevant
   questions: a **house/college** lump sum (years until needed, amount, share
   of savings and assets), **retirement** income (retirement age, spending
   wanted per year), or a **bequest**. Any savings or assets not assigned to
   a goal flow to retirement automatically, so nothing falls through the
   cracks.

2. **Map information to a portfolio.** Each goal gets its own bucket with
   its own glide path that de-risks every year as the date approaches.
   Lump-sum goals hold 90% stocks when 25+ years out, gliding to 0% stocks
   and 100% cash in the last two years. Retirement money glides from 90%
   stocks to 45% on the retirement date and holds 10% cash (about two years
   of spending) thereafter, capped at 60% stocks. The risk score tilts every
   point on the glide path by up to plus or minus 15 points of equity.
   Capital market assumptions: stocks 7% return / 16% vol, bonds 4% / 6%,
   cash 3% / 1%, inflation 2.5%.

2b. **Loans: pay down or invest?** The client lists any loans (balance,
   APR, minimum payment). The savings rate is assumed to be what is left
   after minimum payments. Any loan at or above a 6% APR hurdle is attacked
   with all savings, highest rate first (the "avalanche" method), because a
   guaranteed 6%+ beats the risky 7% expected from stocks. Cheaper loans
   (a 3.5% mortgage, a 5.5% student loan) get minimum payments only while
   the savings are invested. The robo reports net worth, the debt-free year,
   the interest saved versus minimum payments, and how much savings is
   diverted from goals. For house goals it also checks affordability: the
   down payment implies a home price and mortgage, and the monthly cost with
   taxes and upkeep is compared with the 28%-of-income guideline.

3. **Project and display.** 2,000 Monte Carlo paths of log-normal returns
   give a median and a 10th to 90th percentile band for each goal. For
   retirement goals the robo solves for the largest inflation-indexed
   spending that survives to age 95 with 85% probability, and reports the
   probability that the client's desired spending lasts. The Monte Carlo
   uses the year-by-year glide-path weights. Output is a text report plus a
   chart per persona (allocation today, glide path, projection fan chart),
   or the same analysis as an interactive Streamlit page.

## Advice for the three personas

Assumptions I added to make the cases concrete are shown in italics.

### a) 30-year-old, house in 2 years, retire in 35 years
*Assets $40K, income $90K growing 3%/yr, saves 20% until the house then 15%,
wants a $60K down payment and $70K/yr (today's dollars) in retirement with
$25K/yr Social Security. Owes $4K on a credit card at 22% and $30K in student
loans at 5.5%. Moderate risk score 3.4.*

| Goal | Portfolio | Projection | Advice |
|---|---|---|---|
| Debt | Credit card paid off with the first year's savings; student loan at minimum | Debt-free in 10 years; $3.1K interest saved | A 22% card is a guaranteed 22% return, so it goes first. The 5.5% student loan is below the hurdle: pay the minimum and invest. |
| House down payment (2 yrs) | 100% cash (high-yield savings / T-bills) | Median $55.2K vs $60K target | Save about $2.8K/yr more, or shop cheaper. A $60K down payment implies a $300K home at about $1,900/month all-in, 24% of income, so the mortgage is affordable. |
| Retirement (35 yrs) | 93% stocks today, gliding to 48/42/10 at 65 | Median $2.04M at 65 ($858K in today's dollars); 10th pct $1.25M | Supports about $32K/yr in today's dollars plus $25K Social Security, about $13K/yr short of the $70K goal. Raise the post-house savings rate to roughly 18-20%. |

### b) 55-year-old retirement investor with $200K
*Income $110K growing 2%, saves 15%, retires at 65, wants $70K/yr with
$30K/yr Social Security. Owes $150K on a 3.5% mortgage. Moderate risk score 3.2.*

| Goal | Portfolio | Projection | Advice |
|---|---|---|---|
| Retirement at 65 (10 yrs) | 64% stocks today, gliding to 46/43/10 at 65 | Median $566K at 65 (10th pct $424K, 90th pct $765K) | At 85% confidence the pot supports only about $17K/yr in today's dollars, plus $30K Social Security, so roughly $23K/yr short. Options: save 25%+ of income, work to 67-68, or plan on about $47K/yr of spending.  |

This persona is the one the robo should push back on hardest: $200K at 55 is
well behind the usual rule of thumb of about 7x salary. The mortgage is cheap
(3.5%), so the robo says keep paying the minimum and invest, but it is not paid
off until year 14, four years into retirement, which is a real budget issue the
spending plan should reflect.

### c) 70-year-old retiree with $2 million
*Wants $120K/yr of spending with $40K/yr Social Security, so an $80K/yr
withdrawal (4.0% initial withdrawal rate). Risk score 3.8 (aggressive, but
capped for a retiree).*

| Goal | Portfolio | Projection | Advice |
|---|---|---|---|
| Retirement spending (to age 95) | 51% stocks / 39% bonds / 10% cash | 91% probability money lasts 25 years; median $1.9M left at 95 | Plan is sustainable. Could spend up to about $126K/yr at the 85% confidence level. Keep two years of spending in cash, rebalance annually, and think about a bequest or charitable plan given the likely leftover balance. |

## Important features I did not have time to add

- **Life expectancy.** Everyone is planned to age 95. A real robo would use an
  actuarial table (and health, gender, smoking) and plan to a percentile of
  remaining life, or price an annuity for longevity risk.
- **Marital status and dependents.** No joint life expectancy, spousal Social
  Security, survivor needs, or college goals for children.
- **Tax status of accounts.** 401(k) / IRA, Roth and taxable money are all
  treated the same. Taxes change the after-tax value of each dollar, the
  optimal withdrawal order, required minimum distributions at 73, and
  the Roth conversion decision.
- **Real estate.** The house for persona A is only a down-payment goal; the
  mortgage, home equity, property taxes and the choice to rent vs buy are
  ignored. For persona C, home equity could be a reverse-mortgage backstop.
- **Social Security claiming age** (62 vs 67 vs 70) and pensions.
- **Debt is only partly handled.** The pay-down-versus-invest rule uses a single
  6% hurdle and annual steps; a real robo would consider tax deductibility
  (mortgage interest, student loan interest), refinancing, the psychological
  "snowball" alternative, and an emergency fund before extra payments.
- **Dynamic spending rules** in retirement (guardrails) instead of a fixed
  inflation-indexed withdrawal, and sequence-of-returns protection.
- **Better capital market assumptions**: fat tails, mean reversion, more
  asset classes (international, TIPS, real estate), fees, and the current
  yield curve instead of fixed expected returns.
- **Behavioral checks**: the risk quiz measures willingness to take risk, but
  the robo should also compute the *capacity* and *need* for risk and warn
  when they disagree (persona C is "aggressive" but does not need to be).
- **Rebalancing, tax-loss harvesting, and ongoing monitoring**, which are the
  features real robos like Betterment and Wealthfront actually charge for.

## What changed after testing it on myself

Running the first version on my own numbers exposed three design flaws, which
this version fixes: (1) free-form goal fields let me type annual spending for
a house, so goals are now typed; (2) only 30% of my savings had been assigned
to any goal and the rest silently vanished, so unassigned money now flows to
retirement with a note; (3) the allocation was fixed for 38 years and then
jumped, so each goal now follows a glide path. The Streamlit app was added so
the demo in class is sliders and live charts rather than a terminal.

A later round added loans, because in reality most 30-year-olds are deciding
between paying off debt and investing, not just how to invest. The robo now
treats paying off a high-rate loan as a guaranteed-return investment and
budgets savings accordingly, and checks whether the house a client is saving
for is one they can afford to carry.
