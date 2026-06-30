# API Reference

This document outlines the REST API endpoints exposed by the PhantomClaw FastAPI backend. All responses are strictly typed via Pydantic schemas.

## 1. System Health
Verify application readiness, database connectivity, and pipeline availability.

- **Method:** `GET`
- **Route:** `/health`
- **Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "3.0"
}
```

## 2. Market Data
Retrieve the latest price snapshot and technical indicators for a specific ticker.

- **Method:** `GET`
- **Route:** `/market/{symbol}`
- **Validation:** `symbol` must be a valid string between 1-20 characters.
- **Response:** `200 OK`
```json
{
  "symbol": "AAPL",
  "current_price": 150.25,
  "open": 149.00,
  "high": 151.00,
  "low": 148.50,
  "close": 150.00,
  "volume": 1205000,
  "rsi": 45.2,
  "ema20": 148.5,
  "ema50": 142.1,
  "macd": 1.2,
  "atr": 2.5
}
```
- **Errors:** `404 Not Found` if data cannot be retrieved.

## 3. Trigger AI Pipeline
Execute the full multi-agent decision pipeline for a ticker. This triggers market data fetching, agent consensus, risk evaluation, and paper execution.

- **Method:** `POST`
- **Route:** `/analyze/{symbol}`
- **Response:** `200 OK`
```json
{
  "trade_recommendation": {
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 10,
    "confidence": 85.0,
    "reason": "Strong momentum and bullish crossover."
  },
  "execution_decision": {
    "decision": "EXECUTE",
    "reason": "Trust exceeds threshold."
  },
  "risk_assessment": {
    "risk_score": 45.0,
    "risk_level": "MED"
  },
  "trust_assessment": {
    "trust_score": 80.0,
    "trust_level": "HIGH"
  }
}
```
- **Errors:** `500 Internal Server Error` if the pipeline aborts.

## 4. Portfolio State
Retrieve the current buying power and open paper trading positions.

- **Method:** `GET`
- **Route:** `/portfolio`
- **Response:** `200 OK`
```json
{
  "cash": 95000.0,
  "initial_cash": 100000.0,
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 10,
      "average_entry_price": 150.0,
      "realized_pnl": 0.0
    }
  ]
}
```

## 5. Trade Ledger & Analytics
Retrieve the raw execution logs and the server-side computed performance analytics.

- **Method:** `GET`
- **Route:** `/ledger`
- **Response:** `200 OK`
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2026-06-30T10:00:00Z",
      "symbol": "AAPL",
      "side": "BUY",
      "quantity": 10,
      "price": 150.0,
      "fees": 1.5,
      "slippage": 0.5
    }
  ],
  "metrics": {
    "total_trades": 1,
    "win_rate": 0.0,
    "profit_factor": 0.0,
    "sharpe_ratio": 0.0,
    "total_return_pct": -0.01
  }
}
```
