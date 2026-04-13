# 1Password-backed `.env` for ParkingBreaker

This repo stores **no live secrets** in git. Use the [1Password CLI](https://developer.1password.com/docs/cli) to materialize a local `.env` from `.env.op.template`.

## One-time setup

1. Install and sign in: `op signin` (or use the desktop app integration).
2. In your vault, create a **single item** titled exactly **`ParkingBreaker`**.
3. Add **text** fields whose **labels match** the last segment of each `op://VAULT/ParkingBreaker/FIELD` reference in `.env.op.template` (for example `SECRET_KEY`, `STRIPE_SECRET_KEY`, `DATABASE_URL`).
4. Run (pick one):
   - **Recommended:** set your vault name only at inject time — no edits to the committed template:

```bash
OP_VAULT=Private ./scripts/render-env-from-1password.sh
```

- **Or** replace every `REPLACE_ME_VAULT` in `.env.op.template` with your vault name, then `./scripts/render-env-from-1password.sh`.

This writes **`.env`** at the repo root (gitignored) with mode `600`.

## Cursor / IDE

The 1Password for VS Code/Cursor extension can use **beforeShellExecution** hooks so terminal commands do not paste secrets into chat history. Prefer `op run` or this inject flow over typing keys manually.

## Field notes

- **`DATABASE_URL`**: Store the full URL (e.g. `postgresql+psycopg://postgres:…@db:5432/parkingbreaker` for Docker). It must stay consistent with `POSTGRES_PASSWORD` for Compose.
- **`STRIPE_CONNECT_WEBHOOK_SECRET`**: Use a placeholder in 1Password until Connect is enabled, or leave a minimal value if your `op inject` requires non-empty fields.
- **`REDIS_URL`**: Template uses the local Compose default. For Railway, put the plugin URL in a 1Password field and switch the template line to `op://…/REDIS_URL` or override after inject.
- **Optional integrations** you do not use: store an empty string in that field, or remove those lines from your personal template copy (do not commit secrets to work around this).

## Production (Railway)

Railway variables are still set in the Railway dashboard or via their CLI — not from this file. This workflow is for **local** and **agent-safe** secret handling; mirror values from 1Password when configuring hosted envs.
