"""
Streamlit web interface for the FINC6580 robo advisor.

Run:  streamlit run app.py

Pages
    Class Personas      the three clients from the assignment
    Build Your Profile  onboarding -> accounts -> goals -> loans -> risk -> recommendation
    Methodology         how inputs map to advice (explainability), assumptions, limitations
"""

import streamlit as st

import robo_advisor as ra
import ui

st.set_page_config(page_title="Ascend", layout="wide")
ui.inject_css()


# ----------------------------------------------------------------------------
# Page 1: the assignment personas
# ----------------------------------------------------------------------------
def page_personas() -> None:
    ui.hero("Sample Clients", "Three representative clients at different life stages, planned by the same engine.")
    personas = ra.demo_profiles()
    analyses = [ra.analyze_client(p) for p in personas]

    # comparison strip
    st.markdown('<div class="section-title">At a glance</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for col, p, (results, notes, debt, reserve) in zip(cols, personas, analyses):
        with col, st.container(border=True):
            main = results[-1]
            score = ui.overall_score(results)
            tone = "good" if score >= 85 else "warn" if score >= 60 else "bad"
            st.markdown(f'<div class="section-title">{p.name}</div>'
                        f'<div class="section-sub">Age {p.age} | assets {ra.fmt(p.current_assets)} | {p.risk_label} investor</div>'
                        f'<span class="pill {tone}">Plan score {score:.0f}</span>', unsafe_allow_html=True)
            st.markdown(f'<div class="fact">Portfolio today: {", ".join(f"{a} {w:.0%}" for a, w in zip(ra.ASSETS, main["weights_now"]))}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="fact">{main["advice"][0]}</div>', unsafe_allow_html=True)

    st.write("")
    tabs = st.tabs([f"{p.name}" for p in personas])
    blurbs = [
        "Wants to buy a home in 2 years and retire in 35. Profile: $40K in assets, $90K income, saving 20% until the purchase and 15% after, "
        "a $60K down payment target, $70K a year in retirement with $25K of Social Security, a 22% credit card balance and a 5.5% student loan.",
        "Ten years from retirement with $200K saved. Profile: $110K income, saving 15%, retiring at 65 on $70K a year with $30K of Social Security, "
        "and a $150K mortgage at 3.5%.",
        "Retired with $2 million. Profile: wants $120K a year with $40K of Social Security and carries no debt.",
    ]
    for i, (tab, p, (results, notes, debt, reserve), blurb) in enumerate(zip(tabs, personas, analyses, blurbs)):
        with tab:
            st.markdown(f'<div class="section-sub">{blurb}</div>', unsafe_allow_html=True)
            ui.dashboard(p, results, notes, debt, reserve, key=f"p{i}_")
    ui.footer()


# ----------------------------------------------------------------------------
# Page 2: build your own profile
# ----------------------------------------------------------------------------
def page_profile() -> None:
    ui.hero("Plan Builder", "Verify your identity, connect your accounts, set your goals and get a plan that updates as you type.")

    with st.sidebar:
        st.markdown("### Get started")
        st.caption("Your plan updates as you go.")

        with st.expander("1. Verify your identity", expanded=True):
            name = st.text_input("Full name", "Client")
            age = st.number_input("Age", 18, 100, 30)
            attested = st.checkbox("I confirm the information I provide is accurate", value=False)
            kyc = ra.kyc_check(name, int(age), attested)
            st.caption("Prototype: identity and sanctions checks are simulated.")

        with st.expander("2. Connect your accounts", expanded=True):
            st.caption("Prototype: enter balances manually. The production version links accounts directly.")
            assets = st.number_input("Investable assets: cash, brokerage, 401(k), IRA ($)", 0, 50_000_000, 40_000, step=5_000)
            income = st.number_input("Annual gross income ($)", 0, 5_000_000, 90_000, step=5_000)
            sr_now = st.slider("Savings rate now (% of income, after loan minimums)", 0, 60, 15) / 100
            sr_year = st.number_input("Years until your savings rate changes (0 = never)", 0, 50, 0)
            sr_fut = st.slider("Savings rate after the change (%)", 0, 60, 15) / 100 if sr_year else sr_now
            growth = st.slider("Expected income growth (%/yr)", 0.0, 10.0, 3.0, 0.5) / 100
            other = st.number_input("Expected Social Security / pension (per year, today's dollars)", 0, 500_000, 0, step=1_000)

        with st.expander("3. Risk profile", expanded=False):
            answers = []
            for i, (q, opts) in enumerate(ra.RISK_QUESTIONS):
                answers.append(st.select_slider(q, options=[1, 2, 3, 4, 5], value=3,
                                                format_func=lambda v, o=opts: f"{v}: {o[v - 1]}", key=f"risk{i}"))

        with st.expander("4. Planning preferences", expanded=False):
            plan_to = st.select_slider("Plan to age", options=[85, 90, 95, 100], value=ra.PLAN_TO_AGE)
            confidence = st.select_slider("Required confidence", options=[0.75, 0.85, 0.95], value=ra.SUCCESS_TARGET,
                                          format_func=lambda v: f"{v:.0%}")

    # goals and loans live in the main column so there is room
    g_col, l_col = st.columns([1.5, 1])
    with g_col, st.container(border=True):
        st.markdown('<div class="section-title">Goals</div><div class="section-sub">Savings and assets you do not assign are directed to retirement.</div>', unsafe_allow_html=True)
        n_goals = st.number_input("Number of goals", 1, 4, 2)
        goals = []
        gcols = st.columns(int(n_goals))
        defaults = [("house", "House down payment"), ("retirement", "Retirement at 65"), ("college", "College fund"), ("bequest", "Legacy")]
        for i, col in enumerate(gcols):
            with col:
                dk, dn = defaults[i]
                kind = st.selectbox("Type", list(ra.GOAL_KINDS), index=list(ra.GOAL_KINDS).index(dk),
                                    format_func=lambda k: ra.GOAL_KINDS[k], key=f"kind{i}")
                gname = st.text_input("Name", dn if kind == dk else kind.title(), key=f"name{i}")
                if kind == "retirement":
                    retire_age = st.number_input("Retirement age", int(age), 100, max(65, int(age)), key=f"ra{i}")
                    spend = st.number_input("Spending wanted per year (today's dollars)", 0, 2_000_000, 60_000, step=5_000, key=f"sp{i}")
                    goals.append(ra.Goal(gname, kind, int(retire_age - age), 0.0, float(spend), 0.0, None, 0.0))
                elif kind == "bequest":
                    ss = st.slider("Share of savings (%)", 0, 100, 10, key=f"ss{i}") / 100
                    sa = st.slider("Share of assets (%)", 0, 100, 10, key=f"sa{i}") / 100
                    goals.append(ra.Goal(gname, kind, max(ra.PLAN_TO_AGE - int(age), 1), 0.0, 0.0, ss, None, sa))
                else:
                    yrs = st.number_input("Years until needed", 1, 60, 5, key=f"yrs{i}")
                    target = st.number_input("Lump sum needed ($)", 0, 50_000_000, 60_000, step=5_000, key=f"tg{i}")
                    ss = st.slider("Share of savings until then (%)", 0, 100, 50, key=f"ss{i}") / 100
                    sa = st.slider("Share of current assets (%)", 0, 100, 50, key=f"sa{i}") / 100
                    goals.append(ra.Goal(gname, kind, int(yrs), float(target), 0.0, ss, 0.0, sa))

    with l_col, st.container(border=True):
        st.markdown('<div class="section-title">Loans</div><div class="section-sub">Balance, rate and required minimum payment.</div>', unsafe_allow_html=True)
        n_loans = st.number_input("Number of loans", 0, 4, 0)
        loans = []
        for i in range(int(n_loans)):
            with st.container(border=True):
                lkind = st.selectbox("Loan type", list(ra.LOAN_KINDS), index=1, key=f"lk{i}")
                a, b = st.columns(2)
                lname = a.text_input("Name", lkind.title(), key=f"ln{i}")
                bal = b.number_input("Balance ($)", 0, 5_000_000, 10_000, step=1_000, key=f"lb{i}")
                apr = a.slider("APR (%)", 0.0, 30.0, ra.LOAN_KINDS[lkind] * 100, 0.25, key=f"la{i}") / 100
                monthly = b.number_input("Minimum ($/month)", 0, 50_000, max(int(bal * 0.02), 1), step=25, key=f"lm{i}")
                loans.append(ra.Loan(lname, lkind, float(bal), apr, float(monthly) * 12))

    client = ra.ClientProfile(name, int(age), float(assets), float(income), sr_now, sr_fut, int(sr_year), growth,
                              goals, answers, float(other), loans, int(plan_to), float(confidence))
    with st.spinner("Running Monte Carlo simulations..."):
        results, notes, debt, reserve = ra.analyze_client(client)

    st.write("")
    ui.dashboard(client, results, notes, debt, reserve, kyc=kyc)

    if kyc["passed"]:
        report = ra.format_report(client, results, notes, debt)
        st.download_button("Download plan summary", report, file_name=f"{ra.slug(client.name)}_plan.txt")
    ui.footer()


# ----------------------------------------------------------------------------
# Page 3: methodology and explainability
# ----------------------------------------------------------------------------
def page_method() -> None:
    ui.hero("Methodology", "Every recommendation can be traced to a rule you can read.")
    ui.eyebrow("How recommendations are made")
    st.markdown("""
Advice that cannot be explained cannot be audited, so the platform uses transparent rules on top of a Monte Carlo engine.
Every recommendation traces back to an input:

| Input | Rule | Output |
|---|---|---|
| Years until a goal | Glide path: 90% stocks 25+ years out, gliding to 45% on the retirement date (or 0% two years before a lump-sum purchase) | Stock / bond / cash mix for every future year |
| Risk questionnaire (5 answers, 1-5) | Average score tilts every point on the glide path by up to ±15 points of stocks | Conservative / Moderate / Aggressive tilt |
| Loan APR | At or above the 6% hurdle, pay down with savings first (a guaranteed 6%+ beats the risky 7% expected from stocks); below it, pay the minimum and invest | Savings available for goals each year |
| Down payment | Implied home price (20% down) and 30-year mortgage at 6.5%; housing cost compared with 28% of income | Affordable / too expensive |
| Projected balance at retirement | Largest inflation-indexed withdrawal that survives to the planning age (default 95) at the required confidence (default 85%) | Sustainable income vs the spending goal |
| Job stability, reserves, horizon, net worth | Risk *capacity* score; the allocation uses the lower of willingness and capacity (plus a small allowance) | Effective risk score, mismatch warning |
| Income, savings rate, loan minimums | Emergency reserve of 3 to 6 months of living costs is held in cash before anything is invested | Investable assets |
| An under-funded goal | Solve for the savings rate, or the later date, that would fund it | "What it takes" guidance |
""")
    ui.eyebrow("Why 85 percent")
    st.markdown("""
The 85% success threshold is a deliberate trade-off between two errors. Telling a client who is actually fine that they are short
costs them unnecessary saving or a delayed retirement. Telling a client who is actually short that they are fine can leave them
out of money at 90. The second error is far more costly, so the platform is conservative: it requires an 85% probability of
success and plans to age 95.
""")
    ui.eyebrow("Capital market assumptions")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"""
| Asset | Expected return | Volatility |
|---|---|---|
| Stocks | {ra.EXP_RETURN[0]:.1%} | {ra.VOLATILITY[0]:.0%} |
| Bonds | {ra.EXP_RETURN[1]:.1%} | {ra.VOLATILITY[1]:.0%} |
| Cash | {ra.EXP_RETURN[2]:.1%} | {ra.VOLATILITY[2]:.0%} |

Inflation {ra.INFLATION:.1%}. Stock/bond correlation {ra.CORRELATION[0, 1]:.2f}. Returns are log-normal, {ra.N_SIMULATIONS:,} paths per goal.
""")
    with c2:
        st.plotly_chart(ui.frontier_chart([]), use_container_width=True, key="frontier_method")

    ui.eyebrow("Roadmap")
    st.markdown("""
- **Onboarding**: live identity verification and sanctions screening instead of the simulated check.
- **Account linking**: balances, income and loans pulled from institutions instead of typed.
- **Life expectancy** from actuarial tables instead of a flat age 95; **marital status**, dependents and survivor needs.
- **Tax status** of accounts (401(k), Roth, taxable), withdrawal ordering, required minimum distributions.
- **Real estate** as an asset and a liability, rent-vs-buy, home equity in retirement.
- **Debt** detail: deductibility, refinancing, the emotional "snowball" alternative.
- **Dynamic spending rules**, fat-tailed returns, more asset classes, fees, rebalancing and tax-loss harvesting.
- **Risk capacity vs willingness**: the quiz measures willingness; capacity should be computed and the two reconciled.
""")
    ui.footer()


pages = [
    st.Page(page_personas, title="Sample Clients", default=True),
    st.Page(page_profile, title="Plan Builder"),
    st.Page(page_method, title="Methodology"),
]
st.navigation(pages).run()
