"""
app.py
------
Streamlit dashboard for PhantomClaw v2.

This file contains NO business logic. Its only responsibilities are:
  - Render the PhantomClaw user interface.
  - Delegate all analysis to services/analysis_service.run_full_analysis().
  - Display results from the returned FullAnalysisResult.

Architecture:
    Streamlit (app.py)
        ↓
    analysis_service.run_full_analysis()
        ↓
    Pipeline
"""

from __future__ import annotations

import asyncio
import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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

    /* Hide default Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── DB Init ──────────────────────────────────────────────────────────────────

init_db()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<h2 style='color:#e6edf3;margin-bottom:0.25rem'>📈 PhantomClaw</h2>"
        "<p style='color:#8b949e;font-size:0.82rem;margin-top:0'>v2 · AI Trading Intelligence</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='pc-divider'>", unsafe_allow_html=True)

    symbol_input = st.text_input(
        "Ticker Symbol",
        value="AAPL",
        placeholder="e.g. AAPL, TSLA, NVDA",
        help="Enter any valid stock ticker symbol.",
    ).strip().upper()

    analyze_clicked = st.button("🔍 Analyze", use_container_width=True, type="primary")

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


# ─── DB Init (once per session) ──────────────────────────────────────────────

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _risk_color(level: str) -> str:
    return {"HIGH": "risk-high", "MEDIUM": "risk-medium", "LOW": "risk-low"}.get(
        level.upper(), "risk-low"
    )


@st.cache_data(ttl=300)
def get_chart_data(symbol: str):
    """Fetch 3-month OHLCV data, cached for 5 minutes to avoid redundant API calls."""
    return fetch_market_data(symbol, period="3mo", interval="1d")


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
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        margin=dict(l=0, r=0, t=32, b=0),
        xaxis_rangeslider_visible=False,
        title=dict(
            text=f"{symbol} — 3-Month Price History",
            font=dict(color="#e6edf3", size=14),
        ),
        xaxis=dict(gridcolor="#30363d", color="#8b949e"),
        yaxis=dict(gridcolor="#30363d", color="#8b949e"),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_result(result: FullAnalysisResult, symbol: str) -> None:
    """Render all 8 dashboard sections from a FullAnalysisResult."""

    rec       = result.trade_recommendation
    challenge = result.challenge_result
    risk      = result.risk_assessment
    trust     = result.trust_assessment
    decision  = result.execution_decision
    market    = result.market_snapshot
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


def _render_history() -> None:
    """Render the trade history table."""
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


# ─── Analysis Trigger ─────────────────────────────────────────────────────────

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

# ─── Results ──────────────────────────────────────────────────────────────────

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

# ── 8. Trade History (always visible) ─────────────────────────────────────────
_render_history()
