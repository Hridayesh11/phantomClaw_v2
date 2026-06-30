# Project Roadmap

PhantomClaw is developed in distinct, iterative phases. 
*Do not submit PRs for Future Research items until the active Current Version phases are complete.*

## ✅ Completed (Phases 1 - 6)

- **Phase 1-3:** FastAPI Backend Architecture, Multi-Agent AI Pipeline, Upstox Market Data Integration.
- **Phase 4-5:** Modular Paper Trading Engine (Broker, Portfolio, Ledger, Performance Analytics).
- **Phase 6:** Professional Next.js Trading Terminal. Abstracted data fetching into React hooks, created Dashboard, Market Monitor, Trade Ledger, and AI Recommendation panels.

## 🔄 Current Version Focus

- **UI Polish:** Finalizing application screenshots and UI mockups for documentation.
- **V1 RC Stabilisation:** Addressing any minor UI bugs or dependency upgrades prior to the official 1.0 Release Candidate.

## 📅 Short-Term (Planned)

- **Phase 7: Live Broker Integration**
  - Subclass `BaseBroker` to create `UpstoxLiveBroker` and `AlpacaBroker`.
  - Implement real OAuth flows and order routing.
- **Phase 8: WebSocket Integration**
  - Upgrade FastAPI routes to broadcast state changes via WebSockets.
  - Refactor Next.js React Hooks to subscribe to these channels, replacing HTTP polling.

## 📅 Long-Term (Planned)

- **Phase 9: Backtesting Engine**
  - Build a high-performance loop to replay the AI Pipeline across multi-year datasets.
  - Separate backtest `PortfolioManager` instances from the live paper trading instance.

## 🔬 Future Research

- **Vector Trade Memory (ChromaDB):**
  - An empty `save_memory()` hook currently exists in the pipeline.
  - Research implementing ChromaDB to vectorize the LLM's trade reasoning and outcome (`trade_logs`).
  - This will allow the OpenClaw agent to perform RAG (Retrieval-Augmented Generation) on its own past mistakes before formulating a new thesis.
