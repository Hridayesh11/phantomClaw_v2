"""
app.py
------
Streamlit multi-tab dashboard for PhantomClaw v2.

Tabs:
  1. Live Analysis  — full AI pipeline via run_full_analysis()
  2. Backtesting    — deterministic simulation via run_backtest()
  3. Analytics      — historical trade analytics from the database

This file contains NO business logic. No OpenAI calls. No DB writes.

Architecture:
    Streamlit (app.py)
        ↓ tab 1          ↓ tab 2             ↓ tab 3
    run_full_analysis()  run_backtest()   get_recent_trades()
        ↓                    ↓
    Pipeline           Backtest Engine
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from backtesting.backtest_engine import run_backtest
from database.db import get_recent_trades, init_db
from market.market_data import fetch_market_data, validate_symbol
from models.trade_model import FullAnalysisResult
from services.analysis_service import run_full_analysis

logger = logging.getLogger(__name__)


# ─── Safe Async Execution ─────────────────────────────────────────────────────

def run_analysis_sync(symbol: str) -> FullAnalysisResult:
    """
    Run run_full_analysis() safely from a synchronous Streamlit context.

    asyncio.run() raises RuntimeError when an event loop is already running
    (common in some Streamlit environments). Creating and closing a dedicated
    loop avoids that conflict.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_full_analysis(symbol))
    finally:
        loop.close()


# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PhantomClaw v2",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global Styles ────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Base */
    [data-testid="stAppViewContainer"] { background: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
    [data-testid="stHeader"] { background: transparent; }

    /* Cards */
    .pc-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .pc-card-title {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 0.75rem;
    }

    /* Decision badge */
    .badge {
        display: inline-block;
        padding: 0.55rem 1.6rem;
        border-radius: 8px;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 0.08em;
    }
    .badge-execute { background: #0d2b0d; color: #3fb950; border: 2px solid #3fb950; }
    .badge-hold    { background: #2d2200; color: #d29922; border: 2px solid #d29922; }
    .badge-block   { background: #2d0d0d; color: #f85149; border: 2px solid #f85149; }

    /* BUY / SELL pill */
    .pill-buy  { background: #0d2b0d; color: #3fb950; padding: 0.25rem 0.9rem;
                 border-radius: 6px; font-weight: 700; font-size: 1rem; }
    .pill-sell { background: #2d0d0d; color: #f85149; padding: 0.25rem 0.9rem;
                 border-radius: 6px; font-weight: 700; font-size: 1rem; }

    /* Risk colours */
    .risk-high   { color: #f85149; font-weight: 700; }
    .risk-medium { color: #d29922; font-weight: 700; }
    .risk-low    { color: #3fb950; font-weight: 700; }

    /* Divider */
    .pc-divider { border: none; border-top: 1px solid #30363d; margin: 1.25rem 0; }

    /* Metric overrides */
    [data-testid="stMetricValue"] { color: #e6edf3; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.78rem; }

    /* Tab styling */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #161b22;
        border-radius: 8px;
        padding: 0.25rem;
        gap: 0.25rem;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        color: #8b949e;
        font-weight: 600;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: #e6edf3;
        background: #30363d;
        border-radius: 6px;
    }

    /* Hide default Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── DB Init (once per session) ───────────────────────────────────────────────

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h2 style='color:#e6edf3;margin-bottom:0.25rem'>📈 PhantomClaw</h2>"
        "<p style='color:#8b949e;font-size:0.82rem;margin-top:0'>v2 · AI Trading Intelligence</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── Live Analysis inputs ───────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>Live Analysis</div>", unsafe_allow_html=True)
    symbol_input = st.text_input(
        "Ticker Symbol",
        value="AAPL",
        placeholder="e.g. AAPL, TSLA, NVDA",
        help="Enter any valid stock ticker symbol.",
        key="live_symbol",
    ).strip().upper()
    analyze_clicked = st.button("🔍 Analyze", use_container_width=True, type="primary", key="live_analyze_btn")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── Backtesting inputs ─────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>Backtesting</div>", unsafe_allow_html=True)
    bt_symbol = st.text_input(
        "Backtest Symbol",
        value="AAPL",
        placeholder="e.g. AAPL, NVDA",
        key="bt_symbol",
    ).strip().upper()
    bt_start = st.date_input(
        "Start Date",
        value=date.today() - timedelta(days=365),
        key="bt_start",
    )
    bt_end = st.date_input(
        "End Date",
        value=date.today() - timedelta(days=1),
        key="bt_end",
    )
    bt_cash = st.number_input(
        "Initial Capital ($)",
        min_value=1_000,
        max_value=10_000_000,
        value=100_000,
        step=10_000,
        key="bt_cash",
    )
    backtest_clicked = st.button("⚡ Run Backtest", use_container_width=True, key="bt_run_btn")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='pc-card-title'>About</div>"
        "<p style='color:#8b949e;font-size:0.82rem;line-height:1.6'>"
        "\"We don't trust AI — we verify it.\"<br><br>"
        "PhantomClaw v2 runs every trade recommendation through a "
        "Challenge Agent, ArmorIQ risk engine, and Adaptive Trust Engine "
        "before reaching the Execution Controller."
        "</p>",
        unsafe_allow_html=True,
    )

# ─── Main Header ──────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#e6edf3;margin-bottom:0.1rem'>📈 PhantomClaw v2</h1>"
    "<p style='color:#8b949e;font-size:1rem;margin-top:0'>Self-Defending AI Trading System</p>",
    unsafe_allow_html=True,
)
st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _risk_color(level: str) -> str:
    return {"HIGH": "risk-high", "MEDIUM": "risk-medium", "LOW": "risk-low"}.get(
        level.upper(), "risk-low"
    )


@st.cache_data(ttl=300)
def get_chart_data(symbol: str):
    """Fetch 3-month OHLCV data, cached for 5 minutes to avoid redundant API calls."""
    return fetch_market_data(symbol, period="3mo", interval="1d")


@st.cache_data(ttl=120)
def get_analytics_data() -> pd.DataFrame:
    """Load recent trades from DB, cached for 2 minutes."""
    rows = get_recent_trades(limit=500)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _dark_layout(fig: go.Figure, title: str = "", height: int = 340) -> go.Figure:
    """Apply the standard dark theme to any Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        margin=dict(l=0, r=0, t=36, b=0),
        title=dict(text=title, font=dict(color="#e6edf3", size=13)),
        xaxis=dict(gridcolor="#30363d", color="#8b949e"),
        yaxis=dict(gridcolor="#30363d", color="#8b949e"),
        font=dict(color="#8b949e"),
        height=height,
    )
    return fig


def _render_price_chart(symbol: str) -> None:
    """Render a dark-themed candlestick chart using cached OHLCV data."""
    df = get_chart_data(symbol)
    if df is None or df.empty:
        st.info("Price chart unavailable — no historical data returned.")
        return

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                increasing_line_color="#3fb950",
                decreasing_line_color="#f85149",
                name=symbol,
            )
        ]
    )
    fig = _dark_layout(fig, f"{symbol} — 3-Month Price History", height=340)
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


# ─── Tab 1 Renderer ───────────────────────────────────────────────────────────

def _render_result(result: FullAnalysisResult, symbol: str) -> None:
    """Render all 8 live-analysis sections from a FullAnalysisResult."""

    rec        = result.trade_recommendation
    challenge  = result.challenge_result
    risk       = result.risk_assessment
    trust      = result.trust_assessment
    decision   = result.execution_decision
    market     = result.market_snapshot
    indicators = result.technical_indicators

    # ── Price Chart ───────────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>Price History</div>", unsafe_allow_html=True)
    _render_price_chart(symbol)
    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)

    # ── 1. Market Snapshot ────────────────────────────────────────────────────
    with col_left:
        st.markdown("<div class='pc-card-title'>📊 Market Snapshot</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Price", f"${market.get('current_price', 0):,.2f}")
        c2.metric("Open",          f"${market.get('open', 0):,.2f}")
        c3.metric("High",          f"${market.get('high', 0):,.2f}")
        c4, c5, _ = st.columns(3)
        c4.metric("Low",    f"${market.get('low', 0):,.2f}")
        c5.metric("Volume", f"{market.get('volume', 0):,}")

    # ── 2. Technical Indicators ───────────────────────────────────────────────
    with col_right:
        st.markdown("<div class='pc-card-title'>📉 Technical Indicators</div>", unsafe_allow_html=True)
        def _fmt(val: float | None, decimals: int = 2) -> str:
            return f"{val:.{decimals}f}" if val is not None else "N/A"

        i1, i2, i3 = st.columns(3)
        i1.metric("RSI (14)",  _fmt(indicators.get("rsi"), 1))
        i2.metric("MACD",      _fmt(indicators.get("macd"), 4))
        i3.metric("ATR (14)",  _fmt(indicators.get("atr"), 2))
        i4, i5, _ = st.columns(3)
        i4.metric("EMA 50",   _fmt(indicators.get("ema50"), 2))
        i5.metric("SMA 20",   _fmt(indicators.get("sma20"), 2))

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── 3. OpenClaw Recommendation ────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>🤖 OpenClaw Recommendation</div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns([1, 1, 2, 4])

    action_class = "pill-buy" if rec.action == "BUY" else "pill-sell"
    r1.markdown(f"<span class='{action_class}'>{rec.action}</span>", unsafe_allow_html=True)
    r2.metric("Quantity",   rec.quantity)
    r3.metric("Confidence", f"{rec.confidence:.1%}")
    with r4:
        st.markdown(
            f"<p style='color:#8b949e;font-size:0.85rem;margin:0.4rem 0 0 0'>"
            f"<b style='color:#e6edf3'>Reason:</b> {rec.reason}</p>",
            unsafe_allow_html=True,
        )

    conf_pct = int(rec.confidence * 100)
    bar_color = "#3fb950" if rec.action == "BUY" else "#f85149"
    st.markdown(
        f"<div style='background:#30363d;border-radius:4px;height:6px;margin-top:0.5rem'>"
        f"<div style='background:{bar_color};width:{conf_pct}%;height:6px;border-radius:4px'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── 4. Challenge Agent ────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>⚔️ Challenge Agent</div>", unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        st.info(f"**✅ Support**\n\n{challenge.support_reasoning}")
    with ch2:
        st.warning(f"**⚠️ Opposition**\n\n{challenge.opposing_reasoning}")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── 5 & 6. ArmorIQ Risk + Trust Engine ───────────────────────────────────
    arm_col, trust_col = st.columns(2)

    with arm_col:
        st.markdown("<div class='pc-card-title'>🛡️ ArmorIQ Risk Engine</div>", unsafe_allow_html=True)
        rk1, rk2 = st.columns(2)
        rk1.metric("Risk Score", risk.risk_score)
        level_cls = _risk_color(risk.risk_level)
        rk2.markdown(
            f"<div style='padding-top:0.9rem'>"
            f"<span class='pc-card-title'>Risk Level</span><br>"
            f"<span class='{level_cls}' style='font-size:1.4rem'>{risk.risk_level}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if risk.risk_factors:
            with st.expander(f"Risk Factors ({len(risk.risk_factors)} triggered)", expanded=False):
                for factor in risk.risk_factors:
                    st.markdown(f"- {factor}")

    with trust_col:
        st.markdown("<div class='pc-card-title'>🔐 Trust Engine</div>", unsafe_allow_html=True)
        tr1, tr2 = st.columns(2)
        tr1.metric("Trust Score", trust.trust_score)
        tr_cls = _risk_color(trust.trust_level)
        tr2.markdown(
            f"<div style='padding-top:0.9rem'>"
            f"<span class='pc-card-title'>Trust Level</span><br>"
            f"<span class='{tr_cls}' style='font-size:1.4rem'>{trust.trust_level}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        trust_pct = trust.trust_score
        trust_bar = "#3fb950" if trust.trust_level == "HIGH" else (
            "#d29922" if trust.trust_level == "MEDIUM" else "#f85149"
        )
        st.markdown(
            f"<div style='background:#30363d;border-radius:4px;height:6px;margin-top:0.75rem'>"
            f"<div style='background:{trust_bar};width:{trust_pct}%;height:6px;border-radius:4px'></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── 7. Final Decision ─────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>🎯 Final Decision</div>", unsafe_allow_html=True)
    badge_class = {
        "EXECUTE": "badge-execute",
        "HOLD":    "badge-hold",
        "BLOCK":   "badge-block",
    }.get(decision.decision, "badge-hold")

    st.markdown(
        f"<div style='margin:0.5rem 0 0.75rem'>"
        f"<span class='badge {badge_class}'>{decision.decision}</span>"
        f"</div>"
        f"<p style='color:#8b949e;font-size:0.87rem;margin:0'>{decision.rationale}</p>",
        unsafe_allow_html=True,
    )

    # ── 8. Why This Trade? (Explainability Layer) ─────────────────────────────
    if result.explanation:
        st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)
        st.markdown("<div class='pc-card-title' style='font-size:1rem;color:#e6edf3'>🔍 WHY THIS TRADE?</div>", unsafe_allow_html=True)
        
        # Agent Breakdown
        st.markdown("<div class='pc-card'>", unsafe_allow_html=True)
        for agent in result.explanation.agent_breakdown:
            color = "#3fb950" if agent.signal == "BUY" else ("#f85149" if agent.signal == "SELL" else "#8b949e")
            
            st.markdown(f"**{agent.agent_name}**")
            st.markdown(
                f"<span style='color:{color};font-weight:bold;font-size:1.1rem'>{agent.signal}</span> "
                f"<span style='color:#8b949e'>({agent.confidence:.0%})</span>", 
                unsafe_allow_html=True
            )
            
            # Confidence bar
            conf_pct = int(agent.confidence * 100)
            st.markdown(
                f"<div style='background:#30363d;border-radius:2px;height:4px;margin:0.3rem 0'>"
                f"<div style='background:{color};width:{conf_pct}%;height:4px;border-radius:2px'></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            
            # Expandable reasoning
            with st.expander("View Reasoning"):
                st.write(agent.reason)
            
            st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)
            
        # Summaries
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk", risk.risk_level)
        c2.metric("Trust", trust.trust_score)
        c3.metric("Decision", result.explanation.final_decision)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 9. Position Sizing ────────────────────────────────────────────────────
    if result.position_sizing:
        pos = result.position_sizing
        st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)
        st.markdown("<div class='pc-card-title' style='font-size:1rem;color:#e6edf3'>📏 POSITION SIZE</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='pc-card'>", unsafe_allow_html=True)
        p1, p2, p3 = st.columns(3)
        p1.metric("Suggested Quantity", f"{pos.quantity:,}")
        p2.metric("Capital Exposure", f"${pos.capital_exposure:,.2f}")
        p3.metric("Position Method", pos.position_method)
        
        st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)
        
        p4, p5, p6, p7 = st.columns(4)
        p4.metric("Portfolio Value", "$100,000.00")  # Simulated default
        p5.metric("Risk Per Trade", f"${pos.risk_amount:,.2f}")
        p6.metric("ATR", f"{pos.atr:.4f}")
        p7.metric("Stop Distance", f"${pos.stop_distance:.4f}")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 10. Portfolio Optimization ────────────────────────────────────────────
    if getattr(result, "portfolio_optimization", None):
        opt = result.portfolio_optimization
        st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)
        st.markdown("<div class='pc-card-title' style='font-size:1rem;color:#e6edf3'>💼 PORTFOLIO OPTIMIZATION</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='pc-card'>", unsafe_allow_html=True)
        o1, o2, o3 = st.columns(3)
        o1.metric("Trade Allowed", "YES" if opt.allowed_trade else "NO")
        o2.metric("Adjusted Quantity", f"{opt.adjusted_quantity:,}")
        o3.metric("Optimization Method", opt.optimization_method)
        
        st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)
        
        o4, o5, o6 = st.columns(3)
        o4.metric("Portfolio Risk %", f"{opt.portfolio_risk_percent:.2f}%")
        o5.metric("Position Risk %", f"{opt.position_risk_percent:.2f}%")
        o6.metric("Capital Exposure %", f"{opt.capital_exposure_percent:.2f}%")
        
        st.markdown("<div style='margin:1rem 0'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#8b949e;font-size:0.87rem;margin:0'><b style='color:#e6edf3'>Reason:</b> {opt.optimization_reason}</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _render_history() -> None:
    """Render the live trade history table."""
    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='pc-card-title'>📋 Trade History</div>", unsafe_allow_html=True)

    rows = get_recent_trades(limit=50)
    if not rows:
        st.info("No trade history yet. Run your first analysis above.")
        return

    df = pd.DataFrame(rows)
    display_cols = [c for c in ["symbol", "action", "risk_score", "trust_score", "decision", "timestamp"] if c in df.columns]
    df_display = df[display_cols].copy()

    if "timestamp" in df_display.columns:
        df_display["timestamp"] = pd.to_datetime(df_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M UTC")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol":      st.column_config.TextColumn("Symbol"),
            "action":      st.column_config.TextColumn("Action"),
            "risk_score":  st.column_config.NumberColumn("Risk Score", format="%d"),
            "trust_score": st.column_config.NumberColumn("Trust Score", format="%d"),
            "decision":    st.column_config.TextColumn("Decision"),
            "timestamp":   st.column_config.TextColumn("Timestamp"),
        },
    )


# ─── Tab 2 Renderer ───────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _cached_equity_chart(equity_curve: list[dict]) -> go.Figure:
    """Render and cache the equity curve line chart."""
    dates   = [e["date"] for e in equity_curve]
    equities = [e["equity"] for e in equity_curve]
    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=equities,
            mode="lines",
            line=dict(color="#3fb950", width=2),
            fill="tozeroy",
            fillcolor="rgba(63,185,80,0.08)",
            name="Portfolio Equity",
        )
    )
    return _dark_layout(fig, "Portfolio Equity Curve", height=360)


def _render_backtest(result: dict) -> None:
    """Render backtest results: metrics, equity curve, trade table."""
    metrics = result["metrics"]
    summary = result["summary"]

    # ── Summary Metrics ───────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>📊 Backtest Summary</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    ret_pct = summary["return_pct"]
    m1.metric("Total Return", f"{ret_pct:+.2f}%", delta=f"{ret_pct:+.2f}%")
    m2.metric("Win Rate",     f"{summary['win_rate']:.1f}%")
    m3.metric("Max Drawdown", f"{summary['max_drawdown']:.2f}%")
    m4.metric("Total Trades", metrics["trade_counts"]["total"])

    es = metrics["equity_stats"]
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Initial Capital", f"${es['start']:,.0f}")
    e2.metric("Final Equity",    f"${es['final']:,.0f}")
    e3.metric("Peak Equity",     f"${es['peak']:,.0f}")
    e4.metric("Trough Equity",   f"${es['trough']:,.0f}")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── Equity Curve ──────────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>📈 Equity Curve</div>", unsafe_allow_html=True)
    if result["equity_curve"]:
        fig = _cached_equity_chart(tuple(result["equity_curve"]))  # type: ignore[arg-type]
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity curve data to display.")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    # ── Trade Table ───────────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>🗂️ Executed Trades</div>", unsafe_allow_html=True)
    trades = result["trade_history"]
    if not trades:
        st.info("No trades were executed during the backtest period.")
        return

    df = pd.DataFrame(trades)
    show_cols = [c for c in ["date", "action", "price", "quantity", "cash_after", "shares_after"] if c in df.columns]
    df_show = df[show_cols].copy()
    if "price" in df_show.columns:
        df_show["price"] = df_show["price"].map(lambda v: f"${v:,.2f}")
    if "cash_after" in df_show.columns:
        df_show["cash_after"] = df_show["cash_after"].map(lambda v: f"${v:,.2f}")

    st.dataframe(df_show, use_container_width=True, hide_index=True)


# ─── Tab 3 Renderer ───────────────────────────────────────────────────────────

def _render_analytics() -> None:
    """Render analytics charts and stats from the historical trade database."""
    df = get_analytics_data()

    if df.empty:
        st.markdown(
            "<div style='text-align:center;padding:4rem 0;color:#8b949e'>"
            "<div style='font-size:3rem'>📊</div>"
            "<p style='font-size:1.1rem;margin-top:0.5rem'>No trade data yet — run some analyses first.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Summary Metrics ───────────────────────────────────────────────────────
    st.markdown("<div class='pc-card-title'>📊 Overview</div>", unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    a1.metric("Total Trades",       len(df))
    a2.metric("Avg Risk Score",     f"{df['risk_score'].mean():.1f}" if "risk_score" in df else "N/A")
    a3.metric("Avg Trust Score",    f"{df['trust_score'].mean():.1f}" if "trust_score" in df else "N/A")

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    chart_l, chart_r = st.columns(2)

    # ── Decision Distribution Pie ─────────────────────────────────────────────
    with chart_l:
        st.markdown("<div class='pc-card-title'>🎯 Decision Distribution</div>", unsafe_allow_html=True)
        if "decision" in df.columns:
            decision_counts = df["decision"].value_counts().reset_index()
            decision_counts.columns = ["decision", "count"]
            color_map = {"EXECUTE": "#3fb950", "HOLD": "#d29922", "BLOCK": "#f85149"}
            fig_pie = px.pie(
                decision_counts,
                names="decision",
                values="count",
                color="decision",
                color_discrete_map=color_map,
                hole=0.45,
            )
            fig_pie = _dark_layout(fig_pie, height=300)
            fig_pie.update_traces(textfont_color="#e6edf3")
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── Top Symbols Bar Chart ─────────────────────────────────────────────────
    with chart_r:
        st.markdown("<div class='pc-card-title'>🏆 Top Symbols</div>", unsafe_allow_html=True)
        if "symbol" in df.columns:
            sym_counts = df["symbol"].value_counts().head(10).reset_index()
            sym_counts.columns = ["symbol", "count"]
            fig_bar = go.Figure(
                go.Bar(
                    x=sym_counts["symbol"],
                    y=sym_counts["count"],
                    marker_color="#3fb950",
                    marker_line_color="#30363d",
                    marker_line_width=1,
                )
            )
            fig_bar = _dark_layout(fig_bar, height=300)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    hist_l, hist_r = st.columns(2)

    # ── Risk Score Histogram ──────────────────────────────────────────────────
    with hist_l:
        st.markdown("<div class='pc-card-title'>🛡️ Risk Score Distribution</div>", unsafe_allow_html=True)
        if "risk_score" in df.columns:
            fig_risk = go.Figure(
                go.Histogram(
                    x=df["risk_score"],
                    nbinsx=20,
                    marker_color="#f85149",
                    marker_line_color="#30363d",
                    marker_line_width=1,
                    opacity=0.85,
                )
            )
            fig_risk = _dark_layout(fig_risk, height=280)
            st.plotly_chart(fig_risk, use_container_width=True)

    # ── Trust Score Histogram ─────────────────────────────────────────────────
    with hist_r:
        st.markdown("<div class='pc-card-title'>🔐 Trust Score Distribution</div>", unsafe_allow_html=True)
        if "trust_score" in df.columns:
            fig_trust = go.Figure(
                go.Histogram(
                    x=df["trust_score"],
                    nbinsx=20,
                    marker_color="#3fb950",
                    marker_line_color="#30363d",
                    marker_line_width=1,
                    opacity=0.85,
                )
            )
            fig_trust = _dark_layout(fig_trust, height=280)
            st.plotly_chart(fig_trust, use_container_width=True)


# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_live, tab_backtest, tab_analytics = st.tabs([
    "🔍 Live Analysis",
    "⚡ Backtesting",
    "📊 Analytics",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab_live:
    if analyze_clicked:
        if not symbol_input:
            st.error("Please enter a ticker symbol before clicking Analyze.")
        else:
            logger.info("Dashboard: analysis requested for %s", symbol_input)
            with st.spinner(f"Running PhantomClaw pipeline for **{symbol_input}**…"):
                try:
                    result: FullAnalysisResult = run_analysis_sync(symbol_input)
                    st.session_state["last_result"] = result
                    st.session_state["last_symbol"] = symbol_input
                    logger.info("Dashboard: analysis complete for %s", symbol_input)
                except ValueError as exc:
                    st.error(f"**Invalid request:** {exc}")
                    logger.warning("Dashboard ValueError for %s: %s", symbol_input, exc)
                except RuntimeError as exc:
                    st.error(f"**Pipeline error:** {exc}")
                    logger.error("Dashboard RuntimeError for %s: %s", symbol_input, exc)
                except Exception as exc:
                    st.error(f"**Unexpected error:** {exc}")
                    logger.exception("Dashboard unexpected error for %s: %s", symbol_input, exc)

    if "last_result" in st.session_state:
        _render_result(st.session_state["last_result"], st.session_state["last_symbol"])
    else:
        st.markdown(
            "<div style='text-align:center;padding:4rem 0;color:#8b949e'>"
            "<div style='font-size:3rem'>🔍</div>"
            "<p style='font-size:1.1rem;margin-top:0.5rem'>Enter a ticker symbol and click <b>Analyze</b> to begin.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── 8. Trade History (always visible) ────────────────────────────────────
    _render_history()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BACKTESTING
# ══════════════════════════════════════════════════════════════════════════════

with tab_backtest:
    if backtest_clicked:
        if not bt_symbol:
            st.error("Please enter a symbol for the backtest.")
        elif bt_start >= bt_end:
            st.error("Start date must be before end date.")
        else:
            logger.info(
                "Dashboard: backtest requested for %s [%s → %s]",
                bt_symbol, bt_start, bt_end,
            )
            with st.spinner(f"Running backtest for **{bt_symbol}** ({bt_start} → {bt_end})…"):
                try:
                    bt_result = run_backtest(
                        symbol=bt_symbol,
                        start_date=bt_start,
                        end_date=bt_end,
                        initial_cash=float(bt_cash),
                    )
                    st.session_state["last_backtest"] = bt_result
                    logger.info("Dashboard: backtest complete for %s", bt_symbol)
                except ValueError as exc:
                    st.error(f"**Invalid backtest parameters:** {exc}")
                    logger.warning("Backtest ValueError: %s", exc)
                except RuntimeError as exc:
                    st.error(f"**Backtest engine error:** {exc}")
                    logger.error("Backtest RuntimeError: %s", exc)
                except Exception as exc:
                    st.error(f"**Unexpected error:** {exc}")
                    logger.exception("Backtest unexpected error: %s", exc)

    if "last_backtest" in st.session_state:
        _render_backtest(st.session_state["last_backtest"])
    else:
        st.markdown(
            "<div style='text-align:center;padding:4rem 0;color:#8b949e'>"
            "<div style='font-size:3rem'>⚡</div>"
            "<p style='font-size:1.1rem;margin-top:0.5rem'>"
            "Configure your backtest in the sidebar and click <b>Run Backtest</b>."
            "</p></div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

with tab_analytics:
    _render_analytics()
