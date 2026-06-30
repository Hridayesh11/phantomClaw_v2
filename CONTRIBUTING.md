# Contributing to PhantomClaw v3

We welcome contributions from the community! PhantomClaw is designed to be a highly modular, professional-grade algorithmic trading platform. 

## Project Setup
1. Fork the repository on GitHub.
2. Clone your fork locally: `git clone https://github.com/your-username/phantomClaw_v2.git`
3. Set up the Python virtual environment and install requirements (see `README.md`).
4. Set up the Next.js frontend dependencies.

## Branch Strategy
We follow a standard Git Flow:
- `main`: Contains production-ready code.
- `develop`: The active integration branch.
- `feature/*`: For new additions (e.g., `feature/alpaca-broker`).
- `bugfix/*`: For fixing issues (e.g., `bugfix/margin-calc-error`).

Always branch off `develop` when creating new features.

## Coding Standards
- **Python:** Strict adherence to PEP-8. All functions must include type hints (`-> dict`). All configuration uses Pydantic.
- **TypeScript:** Use strict typing. Avoid `any`. Do not put data-fetching logic inside React Components; use `hooks/`.
- **SOLID Principles:** Do not bloat classes. Rely on interfaces (`BaseBroker`, `BaseMarketDataProvider`).

## Testing Before Merge
PhantomClaw manages financial logic, meaning failing tests are unacceptable.
- Run `pytest tests/ -v` before submitting a Pull Request.
- Ensure all 180+ tests pass.
- If you are adding a new agent or broker, you **must** include corresponding unit tests mimicking the existing mocking structure.

## Pull Request Process
1. Push your branch to your fork.
2. Open a PR against the `develop` branch.
3. Fill out the PR template describing the *Why* and *How* of your change.
4. Wait for Code Review from a core maintainer.

## Commit Style
Please use Conventional Commits:
- `feat: add Alpaca broker integration`
- `fix: correct FIFO PnL math off-by-one error`
- `docs: update deployment architecture`
