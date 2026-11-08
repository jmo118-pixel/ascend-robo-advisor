"""Shared look-and-feel and chart components for the robo advisor app."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import robo_advisor as ra

PRODUCT = "Ascend"
TAGLINE = "Goals-based wealth planning"
AUTHOR = "Jose Ochoa Tello"
COURSE = "FINC 6580 FinTech, Georgetown MSBA, Fall 2026"

C = {
    "bg": "#0B1220", "panel": "#121C33", "border": "#1F2D4D", "text": "#E6EDF7", "muted": "#8FA3C7",
    "stocks": "#2DD4BF", "bonds": "#818CF8", "cash": "#FBBF24", "debt": "#FB7185", "good": "#34D399",
    "warn": "#F59E0B", "bad": "#F87171", "line": "#5EEAD4", "band": "rgba(45,212,191,0.18)", "band2": "rgba(45,212,191,0.35)",
}
ASSET_COLORS = {"Stocks": C["stocks"], "Bonds": C["bonds"], "Cash": C["cash"]}


# ----------------------------------------------------------------------------
# CSS and page furniture
# ----------------------------------------------------------------------------
def inject_css() -> None:
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
      html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
      [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {{ visibility: hidden; height: 0; }}
      [data-testid="stSidebarNav"] a span {{ font-weight: 500; }}
      .block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1400px; }}
      h1, h2, h3 {{ letter-spacing: -0.01em; }}
      .hero {{ background: linear-gradient(135deg, #0E1A33 0%, #142A4A 55%, #0F3B3A 100%);
               border: 1px solid {C['border']}; border-radius: 18px; padding: 22px 28px; margin-bottom: 18px; }}
      .hero .brand {{ font-size: 0.85rem; letter-spacing: 0.14em; text-transform: uppercase; color: {C['stocks']}; font-weight: 600; }}
      .hero h1 {{ margin: 4px 0 4px 0; font-size: 2.1rem; }}
      .hero .sub {{ color: {C['muted']}; font-size: 1.0rem; }}
      .hero .by {{ color: {C['text']}; font-size: 0.9rem; margin-top: 10px; opacity: 0.9; }}
      .pill {{ display:inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
               border: 1px solid {C['border']}; background: rgba(255,255,255,0.04); margin-right: 6px; }}
      .pill.good {{ color: {C['good']}; border-color: {C['good']}; }}
      .pill.warn {{ color: {C['warn']}; border-color: {C['warn']}; }}
      .pill.bad  {{ color: {C['bad']};  border-color: {C['bad']}; }}
      .kpi {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 14px 16px; }}
      .kpi .label {{ color: {C['muted']}; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      .kpi .value {{ font-size: 1.35rem; font-weight: 700; margin-top: 2px; overflow-wrap: anywhere; line-height: 1.2; }}
      .kpi .delta {{ color: {C['muted']}; font-size: 0.82rem; }}
      .advice {{ border-left: 4px solid {C['stocks']}; background: rgba(45,212,191,0.07); padding: 10px 14px; border-radius: 8px; margin: 6px 0; }}
      .advice.warn {{ border-left-color: {C['warn']}; background: rgba(245,158,11,0.08); }}
      .advice.bad  {{ border-left-color: {C['bad']};  background: rgba(248,113,113,0.08); }}
      .fact {{ color: {C['muted']}; font-size: 0.92rem; margin: 2px 0; }}
      .section-title {{ font-size: 1.25rem; font-weight: 700; margin: 10px 0 2px 0; }}
      .section-sub {{ color: {C['muted']}; font-size: 0.9rem; margin-bottom: 10px; }}
      .eyebrow {{ font-size: 0.72rem; color: {C['muted']}; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600; margin-bottom: 2px; }}
      div[data-testid="stMetric"] {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 14px; padding: 12px 16px; }}
      .footer {{ color: {C['muted']}; font-size: 0.8rem; margin-top: 30px; border-top: 1px solid {C['border']}; padding-top: 10px; }}
    </style>
    """, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f"""
    <div class="hero">
      <div class="brand">{PRODUCT} &nbsp;|&nbsp; {TAGLINE}</div>
      <h1>{title}</h1>
      <div class="sub">{subtitle}</div>
      <div class="by">Designed and built by <b>{AUTHOR}</b></div>
    </div>""", unsafe_allow_html=True)


def footer() -> None:
    st.markdown(f'<div class="footer">{PRODUCT} is a prototype built by {AUTHOR} for {COURSE}. Not financial advice. '
                f'Projections use {ra.N_SIMULATIONS:,} Monte Carlo paths per goal, {ra.INFLATION:.1%} inflation, and a planning horizon to age {ra.PLAN_TO_AGE}.</div>',
                unsafe_allow_html=True)


def esc(text: str) -> str:
    return text.replace("$", r"\$")


def kpi(col, label: str, value: str, delta: str = "") -> None:
    col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
                 f'<div class="delta">{delta}</div></div>', unsafe_allow_html=True)


def advice_box(text: str, tone: str = "good") -> None:
    cls = {"good": "advice", "warn": "advice warn", "bad": "advice bad"}[tone]
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def tone_for(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("fundable", "on track", "sustainable", "affordable", "below the", "guideline, so")):
        return "good"
    if any(k in t for k in ("shortfall", "trim", "above the", "not paid off")):
        return "bad"
    if t.startswith("advice: what it takes"):
        return "good"
    return "warn"


def eyebrow(label: str) -> None:
    st.markdown(f'<div class="eyebrow">{label}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Plotly charts
# ----------------------------------------------------------------------------
def _layout(fig: go.Figure, title: str, height: int = 320, **kw) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15), x=0.01), height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=C["text"], size=12),
        margin=dict(l=10, r=10, t=44, b=10), legend=dict(orientation="h", y=-0.22, x=0, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=C["panel"], font_color=C["text"]), **kw,
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig


def donut(weights: np.ndarray, title: str = "Allocation today") -> go.Figure:
    fig = go.Figure(go.Pie(labels=ra.ASSETS, values=np.round(weights, 3), hole=0.62, sort=False,
                           marker=dict(colors=[ASSET_COLORS[a] for a in ra.ASSETS], line=dict(color=C["bg"], width=2)),
                           textinfo="percent", hovertemplate="%{label}: %{percent}<extra></extra>"))
    eq = weights[0]
    fig.add_annotation(text=f"<b>{eq:.0%}</b><br><span style='font-size:11px'>stocks</span>", showarrow=False, font=dict(size=20))
    return _layout(fig, title, showlegend=True)


def glide(r: dict) -> go.Figure:
    wp, x = r["weight_path"], r["x"][:-1]
    fig = go.Figure()
    for j, a in enumerate(ra.ASSETS):
        fig.add_trace(go.Scatter(x=x, y=wp[:, j], stackgroup="one", name=a, mode="lines",
                                 line=dict(width=0.5, color=ASSET_COLORS[a]), fillcolor=ASSET_COLORS[a],
                                 hovertemplate=f"{a}: %{{y:.0%}}<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_xaxes(title=r["x_label"])
    return _layout(fig, "Glide path: how the mix de-risks over time")


def fan(r: dict) -> go.Figure:
    lo, mid, hi = r["band"]
    lo2, hi2 = r["band_inner"]
    x = r["x"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[hi, lo[::-1]], fill="toself", fillcolor=C["band"],
                             line=dict(width=0), name="10th-90th percentile", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[hi2, lo2[::-1]], fill="toself", fillcolor=C["band2"],
                             line=dict(width=0), name="25th-75th percentile", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=mid, name="Median", mode="lines", line=dict(color=C["line"], width=3),
                             hovertemplate="%{x}: $%{y:,.0f}<extra>median</extra>"))
    g = r["goal"]
    if g.is_lump_sum and g.target_amount > 0:
        fig.add_hline(y=g.target_amount, line_dash="dot", line_color=C["cash"],
                      annotation_text=f"Target {ra.fmt(g.target_amount)}", annotation_font_color=C["cash"])
    fig.update_yaxes(tickprefix="$", tickformat="~s")
    fig.update_xaxes(title=r["x_label"])
    return _layout(fig, "Projected balance (nominal $)")


def gauge(value: float, title: str, suffix: str = "%", good_at: float = 85, max_val: float = 100) -> go.Figure:
    v = float(np.clip(value, 0, max_val))
    color = C["good"] if v >= good_at else (C["warn"] if v >= 0.7 * good_at else C["bad"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v, number=dict(suffix=suffix, font=dict(size=30), valueformat=".0f"),
        gauge=dict(axis=dict(range=[0, max_val], tickcolor=C["muted"]), bar=dict(color=color, thickness=0.35),
                   bgcolor="rgba(255,255,255,0.04)", borderwidth=0,
                   steps=[dict(range=[0, 0.7 * good_at], color="rgba(248,113,113,0.15)"),
                          dict(range=[0.7 * good_at, good_at], color="rgba(245,158,11,0.15)"),
                          dict(range=[good_at, max_val], color="rgba(52,211,153,0.15)")],
                   threshold=dict(line=dict(color=C["text"], width=2), thickness=0.8, value=good_at))))
    return _layout(fig, title, height=240)


def loans_chart(debt: dict) -> go.Figure:
    bal = debt["balances"]; show = min(bal.shape[1], 31); x = np.arange(show)
    fig = go.Figure()
    palette = [C["debt"], C["cash"], C["bonds"], C["muted"]]
    for i, L in enumerate(debt["loans"]):
        fig.add_trace(go.Scatter(x=x, y=bal[i, :show], name=f"{L.name} ({L.apr:.1%})", mode="lines",
                                 line=dict(width=3, color=palette[i % len(palette)]),
                                 hovertemplate="year %{x}: $%{y:,.0f}<extra></extra>"))
    fig.update_yaxes(tickprefix="$", tickformat="~s"); fig.update_xaxes(title="Years from now")
    return _layout(fig, "Loan balances under the plan")


def savings_split(debt: dict) -> go.Figure:
    show = min(len(debt["extra"]), 30); x = np.arange(show)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=debt["extra"][:show], name="To debt paydown", marker_color=C["debt"]))
    fig.add_trace(go.Bar(x=x, y=debt["available"][:show], name="To goals (invested)", marker_color=C["stocks"]))
    fig.update_yaxes(tickprefix="$", tickformat="~s"); fig.update_xaxes(title="Years from now")
    return _layout(fig, "Where each year's savings go", barmode="stack")


def balance_sheet(client: ra.ClientProfile) -> go.Figure:
    debt = sum(L.balance for L in client.loans)
    nw = client.current_assets - debt
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative", "relative", "total"], x=["Assets", "Liabilities", "Net worth"],
        y=[client.current_assets, -debt, nw], text=[ra.fmt(client.current_assets), f"-{ra.fmt(debt)}", ra.fmt(nw)],
        textposition="outside", connector=dict(line=dict(color=C["border"])),
        increasing=dict(marker_color=C["stocks"]), decreasing=dict(marker_color=C["debt"]), totals=dict(marker_color=C["bonds"])))
    fig.update_yaxes(tickprefix="$", tickformat="~s")
    return _layout(fig, "Assets, liabilities and net worth", height=300)


def frontier_chart(results: list[dict]) -> go.Figure:
    pts = ra.frontier()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[p[2] for p in pts], y=[p[1] for p in pts], mode="lines", name="Stock/bond mixes",
                             line=dict(color=C["muted"], width=2, dash="dot"),
                             text=[f"{p[0]:.0%} stocks" for p in pts], hovertemplate="%{text}<br>return %{y:.1%}, risk %{x:.1%}<extra></extra>"))
    for r in results:
        fig.add_trace(go.Scatter(x=[r["sigma"]], y=[r["mu"]], mode="markers+text", name=r["goal"].name,
                                 marker=dict(size=14, color=C["stocks"], line=dict(color=C["bg"], width=2)),
                                 text=[r["goal"].name], textposition="top center", textfont=dict(size=11),
                                 hovertemplate="return %{y:.1%}, risk %{x:.1%}<extra></extra>"))
        if "weights_retirement" in r:
            mu, sig = ra.portfolio_stats(r["weights_retirement"])
            fig.add_trace(go.Scatter(x=[sig], y=[mu], mode="markers", name=f"{r['goal'].name} (at retirement)",
                                     marker=dict(size=12, color=C["bonds"], symbol="diamond", line=dict(color=C["bg"], width=2)),
                                     hovertemplate="return %{y:.1%}, risk %{x:.1%}<extra></extra>"))
    fig.update_xaxes(title="Risk (annual volatility)", tickformat=".0%"); fig.update_yaxes(title="Expected return", tickformat=".1%")
    return _layout(fig, "Risk vs return: where each goal's portfolio sits", height=340)


def wealth_trajectory(client: ra.ClientProfile, results: list[dict], debt: dict) -> go.Figure:
    """Lifetime view: every goal's median balance stacked by age, debt below the line, net worth on top."""
    end_age = max(int(r["lifetime_x"][-1]) for r in results)
    ages = np.arange(client.age, end_age + 1)
    fig = go.Figure()
    total = np.zeros(len(ages))
    palette = [C["stocks"], C["bonds"], C["cash"], C["good"]]
    for i, r in enumerate(results):
        y = np.zeros(len(ages))
        xs = r["lifetime_x"].astype(int) - client.age
        y[xs[xs < len(ages)]] = r["lifetime_median"][xs < len(ages)]
        total += y
        fig.add_trace(go.Scatter(x=ages, y=y, stackgroup="assets", name=r["goal"].name, mode="lines",
                                 line=dict(width=0.5, color=palette[i % len(palette)]),
                                 hovertemplate="age %{x}: $%{y:,.0f}<extra>" + r["goal"].name + "</extra>"))
    if debt["loans"]:
        bal = debt["balances"].sum(axis=0)
        d = np.zeros(len(ages)); n = min(len(bal), len(ages)); d[:n] = -bal[:n]
        fig.add_trace(go.Scatter(x=ages, y=d, name="Debt", mode="lines", fill="tozeroy", fillcolor="rgba(251,113,133,0.25)",
                                 line=dict(width=0.5, color=C["debt"]), hovertemplate="age %{x}: -$%{customdata:,.0f}<extra>debt</extra>",
                                 customdata=-d))
        total = total + d
    fig.add_trace(go.Scatter(x=ages, y=total, name="Net worth (median)", mode="lines",
                             line=dict(color="#FFFFFF", width=2.5), hovertemplate="age %{x}: $%{y:,.0f}<extra>net worth</extra>"))
    for r in results:
        if r["goal"].kind == "retirement" and r["goal"].years_until > 0:
            fig.add_vline(x=client.age + r["goal"].years_until, line_dash="dot", line_color=C["muted"],
                          annotation_text="retire", annotation_position="top", annotation_font_color=C["muted"])
    fig.update_yaxes(tickprefix="$", tickformat="~s"); fig.update_xaxes(title="Age")
    return _layout(fig, "Wealth trajectory: median balances by goal, debt and net worth", height=380)


def cashflow_sankey(client: ra.ClientProfile, results: list[dict], debt: dict) -> go.Figure:
    """Where next year's income goes: living costs, loan minimums, debt paydown, each goal."""
    income = client.annual_income
    if income <= 0:
        return None
    savings = debt["savings"][0]
    extra = debt["extra"][0]
    available = debt["available"][0]
    minimums = sum(L.min_payment for L in client.loans)
    living = max(income - savings - minimums, 0)
    labels = ["Income", "Living costs", "Loan minimums", "Savings", "Debt paydown"] + [r["goal"].name for r in results]
    colors = [C["bonds"], C["muted"], C["debt"], C["stocks"], C["debt"]] + [C["stocks"], C["cash"], C["good"], C["bonds"]][: len(results)]
    src, dst, val = [], [], []
    def link(a, b, v):
        if v > 0:
            src.append(a); dst.append(b); val.append(v)
    link(0, 1, living); link(0, 2, minimums); link(0, 3, savings); link(3, 4, extra)
    for i, r in enumerate(results):
        g = r["goal"]
        link(3, 5 + i, available * g.share_of_savings)
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=18, thickness=16, line=dict(color=C["bg"], width=0.5)),
        link=dict(source=src, target=dst, value=val, color="rgba(143,163,199,0.25)",
                  hovertemplate="%{source.label} to %{target.label}: $%{value:,.0f}<extra></extra>")))
    return _layout(fig, "Year-one cash flow: where your income goes", height=340)


# ----------------------------------------------------------------------------
# Composite sections
# ----------------------------------------------------------------------------
def plan_score(r: dict) -> tuple[float, str, str]:
    """(0-100 score, label, note) summarising how healthy this goal is."""
    g = r["goal"]
    if r["phase"] == "drawdown":
        return r["success"] * 100, "Chance money lasts", f"to age {ra.PLAN_TO_AGE}"
    if g.is_lump_sum:
        return r["target_prob"] * 100, "Chance of hitting target", ra.fmt(g.target_amount)
    if g.kind == "retirement":
        ratio = r["total_income_real"] / g.annual_spending if g.annual_spending else 1.0
        return min(ratio, 1.5) * 100, "Income goal funded", f"{ra.fmt(r['total_income_real'])} of {ra.fmt(g.annual_spending)}/yr"
    return 100.0, "Growth goal", ""


def credit_panel(ch: dict) -> None:
    eyebrow("Credit health")
    st.markdown(f'<div class="section-title">Grade {ch["grade"]} '
                f'<span class="pill {"good" if ch["score"] >= 0.7 else "warn" if ch["score"] >= 0.55 else "bad"}">{ch["score"]:.0%}</span></div>'
                f'<div class="section-sub">The five factors a lender weighs, scored from your profile.</div>', unsafe_allow_html=True)
    for name, what, val, score, note in ch["items"]:
        st.markdown(f"<div style='display:flex;justify-content:space-between;align-items:baseline;margin-top:6px'>"
                    f"<span><b>{name}</b> <span class='fact'>· {what}</span></span><span><b>{val}</b></span></div>",
                    unsafe_allow_html=True)
        st.progress(score / 5, text=note)


def kyc_panel(k: dict) -> None:
    eyebrow("Identity verification")
    pills = "".join(f'<span class="pill {"good" if ok else "bad"}">{label}: {"verified" if ok else "pending"}</span>' for label, ok in k["checks"])
    st.markdown(pills, unsafe_allow_html=True)
    if not k["passed"]:
        st.warning("Verification is incomplete. Recommendations are shown for preview only and the plan cannot be downloaded until every check passes.")


def goal_card(r: dict, idx: int, key: str = "") -> None:
    g = r["goal"]
    with st.container(border=True):
        score, label, note = plan_score(r)
        head, gcol = st.columns([3, 1])
        head.markdown(f'<div class="section-title">Goal {idx}: {g.name}</div>'
                      f'<div class="section-sub">{ra.GOAL_KINDS[g.kind]} · money needed in {g.years_until} years · '
                      f'portfolio today {", ".join(f"{a} {w:.0%}" for a, w in zip(ra.ASSETS, r["weights_now"]))}</div>',
                      unsafe_allow_html=True)
        k1, k2, k3 = head.columns(3)
        kpi(k1, "Expected return", f"{r['mu']:.1%}", f"volatility {r['sigma']:.1%}")
        if r["phase"] == "accumulation":
            kpi(k2, "Median at goal date", ra.fmt(r["p50"]), f"{ra.fmt(r['p50_real'])} in today's dollars")
            if g.kind == "retirement":
                kpi(k3, "Sustainable income", ra.fmt(r["total_income_real"]) + "/yr", f"goal {ra.fmt(g.annual_spending)}/yr, today's $")
            elif g.is_lump_sum:
                kpi(k3, "10th-90th pct range", f"{ra.fmt(r['p10'])} - {ra.fmt(r['p90'])}", "at goal date")
            else:
                kpi(k3, "Contributions", ra.fmt(r["contributions"].sum()), "over the horizon")
        else:
            kpi(k2, "Initial withdrawal rate", f"{r['withdrawal_rate']:.1%}", "of the portfolio")
            kpi(k3, "Max sustainable spending", ra.fmt(r["sustainable_real"]) + "/yr", f"goal {ra.fmt(g.annual_spending)}/yr")
        gcol.plotly_chart(gauge(score, label, "%" if "Chance" in label else "%", good_at=85 if "Chance" in label else 100,
                                max_val=100 if "Chance" in label else 150), use_container_width=True, key=f"{key}gauge{idx}")
        gcol.caption(esc(note))
        c1, c2, c3 = st.columns([1, 1.3, 1.6])
        c1.plotly_chart(donut(r["weights_now"]), use_container_width=True, key=f"{key}donut{idx}")
        c2.plotly_chart(glide(r), use_container_width=True, key=f"{key}glide{idx}")
        c3.plotly_chart(fan(r), use_container_width=True, key=f"{key}fan{idx}")
        for a in r["advice"]:
            advice_box("Advice: " + a, tone_for(a))
        with st.expander("Details and the numbers behind this goal"):
            for f_ in r["facts"]:
                st.markdown(f'<div class="fact">• {f_}</div>', unsafe_allow_html=True)


def debt_section(debt: dict, key: str = "") -> None:
    with st.container(border=True):
        eyebrow("Debt strategy")
        st.markdown('<div class="section-title">Pay down or invest?</div>'
                    f'<div class="section-sub">Loans at or above the {ra.DEBT_HURDLE:.0%} APR hurdle are paid off highest-rate-first with savings before investing; cheaper loans get minimum payments.</div>',
                    unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        dfy = debt["debt_free_year"]
        kpi(k1, "Total debt", ra.fmt(sum(L.balance for L in debt["loans"])), f"{len(debt['loans'])} loan(s)")
        kpi(k2, "Debt-free in", f"{dfy} yrs" if dfy is not None else "30+ yrs", "under this plan")
        kpi(k3, "Interest saved", ra.fmt(max(debt["interest_min_only"] - debt["interest_plan"], 0)), "vs minimum payments only")
        kpi(k4, "Savings diverted to debt", ra.fmt(debt["extra"].sum()), "before investing")
        c1, c2 = st.columns(2)
        c1.plotly_chart(loans_chart(debt), use_container_width=True, key=f"{key}loans")
        c2.plotly_chart(savings_split(debt), use_container_width=True, key=f"{key}split")
        for L, a in zip(debt["loans"], debt["advice"]):
            advice_box("Advice: " + a, "warn" if L.pay_first else "good")


def overall_score(results: list[dict]) -> float:
    """Plan score 0-100: average of goal scores, each capped at 100."""
    scores = [min(plan_score(r)[0], 100) for r in results]
    return float(np.mean(scores)) if scores else 0.0


def dashboard(client: ra.ClientProfile, results: list[dict], notes: list[str], debt: dict, reserve: dict,
              kyc: dict | None = None, key: str = "") -> None:
    """The full recommendation view for one client."""
    ch = ra.credit_health(client)
    total_debt = ch["total_debt"]
    score = overall_score(results)
    eyebrow("Plan summary")
    head, gcol = st.columns([4, 1])
    head.markdown(f'<div class="section-title" style="font-size:1.6rem;margin-top:14px">{client.name}</div>'
                  f'<div class="section-sub">Plan score {score:.0f} of 100 · {len(results)} goal{"s" if len(results) != 1 else ""} · '
                  f'{"debt-free" if not client.loans else f"{len(client.loans)} loan{"s" if len(client.loans) != 1 else ""}"}</div>',
                  unsafe_allow_html=True)
    gcol.plotly_chart(gauge(score, "Plan score", "", good_at=85), use_container_width=True, key=f"{key}score")
    k1, k2, k3, k4, k5 = st.columns(5)
    kpi(k1, "Risk profile", client.risk_label, f"willingness {client.willingness_score:.1f} · capacity {client.capacity_score:.1f}")
    kpi(k2, "Net worth", ra.fmt(ch["net_worth"]), f"assets {ra.fmt(client.current_assets)} · debt {ra.fmt(total_debt)}")
    kpi(k3, "Savings rate", f"{client.savings_rate_now:.0%}", f"{client.savings_rate_future:.0%} after year {client.savings_rate_change_year}" if client.savings_rate_change_year else "of income")
    kpi(k4, "Emergency reserve", ra.fmt(reserve["held"]), f"{reserve['months']} months target {ra.fmt(reserve['target'])}")
    kpi(k5, "Credit health", f"Grade {ch['grade']}", f"debt service {ch['dti']:.0%} of income")
    if kyc:
        kyc_panel(kyc)
    for n in notes:
        st.info(esc(n))

    with st.container(border=True):
        eyebrow("Lifetime view")
        st.plotly_chart(wealth_trajectory(client, results, debt), use_container_width=True, key=f"{key}traj")
        st.markdown('<div class="fact">Median paths only; the goal cards below show the full range of outcomes.</div>', unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.1, 1.4])
    with left:
        eyebrow("Balance sheet")
        st.plotly_chart(balance_sheet(client), use_container_width=True, key=f"{key}bs")
        sk = cashflow_sankey(client, results, debt)
        if sk is not None:
            eyebrow("Cash flow")
            st.plotly_chart(sk, use_container_width=True, key=f"{key}sankey")
    with right:
        credit_panel(ch)

    if debt["loans"]:
        debt_section(debt, key)

    for i, r in enumerate(results, 1):
        goal_card(r, i, key)

    with st.container(border=True):
        eyebrow("Risk and return")
        st.plotly_chart(frontier_chart(results), use_container_width=True, key=f"{key}frontier")
        st.markdown('<div class="fact">Each goal\'s portfolio sits on the stock/bond curve at the point its horizon and your risk score pick. '
                    'Longer horizons sit further up and to the right; money needed soon sits near the cash corner.</div>', unsafe_allow_html=True)
