# Security Policy

PhantomClaw takes the security of financial data and API credentials seriously.

## Responsible Disclosure

If you discover a security vulnerability within PhantomClaw (e.g., an exploit allowing bypassing of margin constraints, or accidental exposure of API keys in logs), please **DO NOT** open a public issue.

Instead, please email the maintainer team directly at `security@phantomclaw-example.com` (Placeholder). We will acknowledge receipt within 48 hours and work to patch the vulnerability before public disclosure.

## Secrets Management & API Key Handling

- **Never Commit Secrets:** The `.env` and `.env.local` files are explicitly added to `.gitignore`. Never commit your Upstox or OpenAI keys.
- **Pydantic Validation:** The application enforces the presence of secrets at runtime via `utils/config.py`. It will crash immediately if started without the required keys, rather than failing silently later in execution.
- **Client-Side Safety:** The Next.js frontend never handles broker or LLM API keys. It only requires `NEXT_PUBLIC_API_URL`. All secret handling is sandboxed entirely within the Python backend.

## Known Limitations

- **Local SQLite Storage:** The SQLite database is currently stored unencrypted on disk. Anyone with filesystem access can view your trading history.
- **Authentication:** The FastAPI backend currently lacks JWT/OAuth user authentication. It assumes the API is running locally and bound to `localhost`. 

## Future Security Improvements

Before deploying PhantomClaw to a public cloud environment, the following must be implemented:
1. Integration of FastAPI `OAuth2PasswordBearer` to secure the REST endpoints.
2. Migration from local `.env` files to a managed secrets provider (AWS Secrets Manager / HashiCorp Vault).
3. Encryption at rest for the database layer.
