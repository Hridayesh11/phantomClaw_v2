# Testing Strategy

PhantomClaw's financial logic demands absolute precision. A small mathematical error in position sizing or margin validation can cause catastrophic simulated or live losses. Therefore, PhantomClaw is backed by a robust `pytest` suite comprising 180+ passing tests.

## Testing Philosophy

- **Determinism First:** Tests mock out stochastic LLM calls (`openai.ChatCompletion`) to ensure the test suite runs instantly and predictably.
- **Fail Closed:** Tests explicitly verify that when dependencies fail (network drops, invalid API keys), the `ExecutionController` fails closed and blocks trading.
- **No Database Mocks for Integration:** Core logic is tested against an in-memory SQLite database (`:memory:`) to ensure SQL constraints and queries execute realistically.

## Pytest Structure

The `tests/` directory mirrors the source code structure:

- `test_trading_broker.py`: Verifies `PaperBroker` applies synthetic fees and slippage correctly.
- `test_trading_portfolio.py`: Tests margin exhaustion, FIFO PnL math, and cash deductions.
- `test_risk_engine.py`: Validates ArmorIQ volatility scoring and position sizing ATR math.
- `test_upstox_provider.py`: Verifies market data formatting, caching, and retry logic.
- `test_agents.py`: Verifies the quantitative agents (Momentum, Trend) output correct signals based on mocked technical indicators.

## Coverage Strategy

- **Unit Tests:** Focus heavily on the math in `market.indicators`, `risk.position_sizer`, and `trading.analytics`.
- **Integration Tests:** The `test_analysis_service.py` executes the entire pipeline end-to-end, mocking only the external HTTP calls.

## Mocking

PhantomClaw uses `unittest.mock` heavily. 
- LLM calls are intercepted via `patch("openai.AsyncOpenAI")`.
- Time is frozen using `freezegun` when testing historical backfills or retry-layer backoff delays.

## Future Integration Testing
Before Live Broker integration (Phase 7), the testing suite will be expanded to include VCR.py (or equivalent) to record and replay exact HTTP responses from the live broker APIs, ensuring the `TradingEngine` can handle specific exchange error codes.
