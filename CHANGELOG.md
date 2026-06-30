# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.0-rc.1] - 2026-06-30
### Added
- Complete suite of architectural documentation (`docs/`).
- `README.md` refined for production-quality open-source release.

## [v0.6.0] - 2026-06-25
### Added
- **Phase 6: Frontend Terminal.** Full Next.js 15 application utilizing Tailwind v4 and `shadcn/ui`.
- Abstracted React query hooks (`useMarketData`, `usePortfolio`, `useLedger`) for future WebSocket integration.
- Performance Analytics dashboard featuring Recharts equity curves.

## [v0.5.0] - 2026-06-15
### Added
- **Phase 5: Trading Engine.** Modular simulated Paper Trading environment.
- Abstract `BaseBroker`, `BaseFeeModel`, and `BaseSlippageModel` classes.
- Singleton `PortfolioManager` to enforce margin constraints.
- `TradeLedger` SQLite persistence for atomic execution tracking.

## [v0.4.0] - 2026-06-01
### Added
- Integration of the `UpstoxProvider` fetching live market data.
- Added `@with_retry` decorator and local response caching to prevent rate-limit failures.
- `InstrumentResolver` mapping raw symbols to exchange keys.

## [v0.3.0] - 2026-05-15
### Added
- FastAPI backend framework established with strict `api/routes` separation.
- Unidirectional orchestration via `analysis_service.py`.

## [v0.2.0] - 2026-05-01
### Added
- Introduction of the Adversarial AI pipeline (`ChallengeAgent`).
- Deterministic risk scaling via `ArmorIQ` and `TrustEngine`.

## [v0.1.0] - 2026-04-15
### Added
- Initial project scaffolding.
- `OpenClaw` LLM agent and basic quantitative indicators (RSI, MACD).
