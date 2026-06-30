# Database Architecture

PhantomClaw uses a localized **SQLite3** database (`phantomclaw.db`) for its persistence layer. 
The database acts as an immutable, append-only ledger, ensuring absolute traceability of both AI logic and financial executions.

## Schema

### 1. `trade_logs` Table
Persists the holistic reasoning and output of the AI Pipeline for every analysis cycle.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `timestamp` | DATETIME | When the analysis occurred |
| `symbol` | TEXT | The evaluated ticker |
| `action` | TEXT | BUY / SELL / HOLD |
| `quantity` | INTEGER | Suggested sizing |
| `confidence` | REAL | Agent conviction |
| `price` | REAL | Market price at time of analysis |
| `rsi`, `macd`, `atr` | REAL | Key technicals |
| `risk_score` | REAL | ArmorIQ output |
| `trust_score` | REAL | Trust Engine output |
| `decision` | TEXT | Final Execution Controller output |
| `reason` | TEXT | Primary LLM reasoning |
| `support_reasoning` | TEXT | Challenge Agent agreement |
| `opposing_reasoning` | TEXT | Challenge Agent dissent |

### 2. `execution_logs` Table
Persists the strict financial transaction resulting from a successful `PaperBroker` execution.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | Primary Key |
| `timestamp` | DATETIME | When the trade filled |
| `symbol` | TEXT | The executed ticker |
| `side` | TEXT | BUY / SELL |
| `quantity` | INTEGER | Executed size |
| `price` | REAL | Effective filled price |
| `fees` | REAL | Synthetic brokerage fee applied |
| `slippage` | REAL | Synthetic slippage applied |

## Persistence Strategy & Relationships
- **Decoupled Writes:** The `trade_logs` table represents *intent* (the AI's choice). The `execution_logs` table represents *reality* (the Broker's fill). They are intentionally decoupled. A trade might be logged in `trade_logs` as `REJECTED`, meaning no corresponding `execution_log` will exist.
- **Append-Only:** Code paths never `UPDATE` or `DELETE` records, enforcing a strict audit trail.

## Future Migrations
The database interaction uses the native `sqlite3` library in `database/db.py`. Migrating to PostgreSQL for production scale will involve replacing the SQLite connection adapter with `asyncpg` or `psycopg2`, while the SQL schema remains largely identical.
