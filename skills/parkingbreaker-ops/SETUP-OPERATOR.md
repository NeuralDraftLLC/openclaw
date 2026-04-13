# Operator secrets (manual — do not commit tokens)

1. Generate a token:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Railway: API service → Variables → `PB_INTERNAL_TOKEN=<token>` → redeploy.
3. OpenClaw vault:
   ```bash
   openclaw vault set PARKINGBREAKER_API_BASE https://fightcitytickets-production.up.railway.app
   openclaw vault set PB_INTERNAL_TOKEN <same token>
   ```
4. Verify:
   ```bash
   curl -sS -H "Authorization: Bearer $PB_INTERNAL_TOKEN" \
     "$PARKINGBREAKER_API_BASE/telemetry/stats/us-ca-san_francisco" | python3 -m json.tool
   ```

See `SKILL.md` for the observer script path.
