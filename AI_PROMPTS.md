# AI Prompts Used to Build the Robo Advisor

AI tool: Claude (Fable 5.1) in the Claude desktop app, Code mode.
Date: November 6, 2026

## Prompt 1 (initial build)

> Help me complete this assignment
> *(attached: FINC6580 MSBA 2026 Week 3 Build your own robo.docx)*

Claude read the assignment and proposed the design: a single Python script
(`robo_advisor.py`) with

1. an intake questionnaire (age, assets, income, current and future savings
   rates, goals with dates and amounts, 5-question risk-tolerance quiz),
2. a mapping from goals + risk score to a stocks / bonds / cash portfolio
   (horizon-based glide path, tilted by the risk score),
3. Monte Carlo projections of accumulation and of retirement spending,
   a "sustainable spending" solver, and PNG charts,
4. the three assignment personas pre-loaded under `--demo`.

## Prompt 2 (review of the first run and fixes)

After the first run, three problems were identified in the output and fixed:

> The retiree portfolio comes out as 3% stocks / 87% bonds because the glide
> path treats "0 years to goal" as cash. Give retirees a 45% equity base
> instead, with the risk tilt on top and a 60% cap.

> Persona A's savings never shift to retirement after the house is bought.
> Add a `share_of_savings_later` field so the retirement goal receives 100%
> of savings after year 2.

> All three personas write to the same `persona_charts.png`. Name the output
> files after each persona.

## Prompt 3 (write-up)

> Summarize the advice for the three personas and list the features that were
> left out (life expectancy tables, marital status, dependents, tax status of
> accounts, real estate, etc.) in a README for the class presentation.

## Notes on how the AI was used

- The capital market assumptions (7% stocks, 4% bonds, 3% cash, 2.5% inflation),
  the glide-path breakpoints, the 85% success target and the persona inputs
  (income, savings rates, spending needs, Social Security) were chosen by me
  as simplifying assumptions; the AI wrote the code around them.
- Every number in the write-up comes from running `python robo_advisor.py --demo`.

## Prompt 4 (improvements after testing the questionnaire myself)

> Is there a way to improve this?

Claude listed six improvements. I chose to build the first three plus a web
interface:

> Also add Streamlit

Changes made in this round:

1. **Goal types.** Goals are now `house`, `college`, `retirement` or `bequest`,
   and the questionnaire asks only the relevant questions (lump sum for a
   house, retirement age and annual spending for retirement). This removed
   the mistake I made in testing, where I typed annual spending for a house.
2. **Auto-allocation.** Any share of savings or assets not assigned to a goal
   flows to retirement, and shares above 100% are scaled down, with a note
   printed. In my own test run only 30% of my savings had been assigned.
3. **Glide path through time.** Each goal's allocation now de-risks every year
   as the date approaches (90% stocks far out, 45% on the retirement date,
   0% stocks in the last two years before a lump-sum purchase), and the Monte
   Carlo uses the year-by-year weights. The chart shows the glide path.
4. **Streamlit app** (`app.py`): sidebar inputs, persona presets, goal cards,
   risk sliders, and interactive plotly charts (allocation, glide path,
   projection fan chart) with the same advice text as the command line.

Earlier fix (Prompt 3b): the questionnaire crashed on `20,000`; it now accepts
commas, `$` and `%` and re-asks on bad input.

## Prompt 5 (loans)

> Not sure if we have the academic freedom based on the instructions, but I
> think loans are also important to maybe add in reality to figure out this
> stuff - if we can add and will add to this project and enhance it please do so

Added a debt module to the engine, questionnaire and Streamlit app:

- A `Loan` (name, type, balance, APR, minimum payment). Savings rate is
  assumed to be after minimum payments.
- Pay-down-versus-invest rule: loans at or above a 6% APR hurdle are paid
  off with savings highest-rate-first before investing; cheaper loans get
  minimum payments. Reports net worth, debt-free year, interest saved
  versus minimums, and savings diverted from goals, with a loan-balance
  chart and a chart of where each year's savings go.
- Goal contributions are now computed from savings left after debt paydown.
- Mortgage affordability check for house goals (implied home price and
  mortgage from the down payment, monthly cost vs 28% of income).
- Personas: A now carries a 22% credit card and a 5.5% student loan; B a
  3.5% mortgage that is not paid off until four years into retirement.

## Prompt 6 (UI redesign and course topics)

> So I like the content, I just want to fix it so that it has the class example
> in one page and the other profiles in the other page. - but I want to improve
> it so that the UI is more intuitive looks fancier, and the graphs are better,
> and it looks more like a financial application for the purpose of fintech and
> what the class is asking. Especially with these topics from class they might
> not all be relevant for this assignment, but I think add them to improve this
> and the colors. Add my name
> *(attached: Course Modules: FinTech.Fall2026.pdf)*

Claude read the course module list and rebuilt the app as a multipage
Streamlit application:

- `app.py` now has three pages: Class Personas, Build Your Profile, Methodology.
- `ui.py` holds a dark navy/teal fintech theme (hero header with my name, KPI
  cards, advice callouts) and plotly charts: donut allocation, glide-path area,
  fan chart with 10-90 and 25-75 bands, plan-health gauge, loan balances,
  savings split, a balance-sheet waterfall, and a risk/return chart.
- Course topics added to the engine: `kyc_check` (simulated AML/KYC gate),
  `credit_health` (a 5 Cs of credit scorecard), `frontier` (portfolio risk /
  return curve), plus an explainability page with a Type I / Type II error
  reading of the success threshold.
- Fixes during testing: duplicate plotly chart keys across persona tabs, a
  stray LaTeX escape inside HTML blocks, and the download button re-running
  the simulation (now reuses the computed results via `format_report`).

## Prompt 7 (product polish)

> Do not make it class topics, make it a real product and remove emoji. make it
> look professional

Rebranded the app as "Horizon Wealth": pages renamed to Sample Clients, Plan
Builder and Methodology; all "Course topic" labels replaced by product section
labels (Identity verification, Balance sheet, Credit health, Debt strategy, Risk
and return); emoji removed from navigation and the page icon; Inter font; the
Streamlit toolbar hidden; persona names changed to client labels; copy rewritten
in customer-facing language. The course credit remains only in the footer.

## Prompt 8 (logic, visuals, name, packaging)

> Help me improve the logic and visualization to make it more visually appealing
> and Name it something better. Once this is done pack all of it into codes I can
> upload like the assignment said and launch it

Renamed the product to **Ascend**. Logic added to the engine: a risk *capacity*
score reconciled with questionnaire *willingness* (allocations use the lower);
an emergency reserve carved out of assets before investing; user-set planning
age and confidence level; a "what it takes" solver that finds the savings rate
or the later date that funds an under-funded goal (with an honest fallback when
no single lever is enough); and a lifetime wealth path per goal (accumulation
followed by drawdown). Visuals added: an overall plan score gauge, a lifetime
wealth-trajectory chart (goals stacked by age, debt below zero, net worth line,
retirement marker), a year-one cash-flow Sankey diagram, a compact credit-health
panel, and layout fixes for narrower screens. Rebuilt the Canvas zip.
