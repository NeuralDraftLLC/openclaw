# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## SSH

- `ssh root@10.0.0.1` — home server (if needed)

## ParkingBreaker / FightCityTickets

- Repo: `/home/amir/homebase/code/FIGHTCITYTICKETS-1/`
- Production: `https://fightcitytickets-production.up.railway.app`
- Railway project: `fightcitytickets-production`
- Frontend: `frontend-production-023c`
- City JSONs: `backend/cities/*.json` (53 cities)
- Proposals queue: `backend/cities_generated/proposals/review/`
- Campaign map: `city-campaign-map.json` (54 entries, all empty — no Reddit campaign IDs yet)
- Pre-commit hook: `hooks/pre-commit` — blocks city JSON commits without approved proposals

## OpenClaw

- Gateway: systemd service, port 18789, loopback-only
- Cron jobs (persisted): `~/.openclaw/cron/jobs.json` — finance alerts: Stripe under $50, Lob under $15; pulse script `FIGHTCITYTICKETS-1/backend/scripts/business-pulse.sh`
- Config: `~/.openclaw/openclaw.json`
- Skills installed (user): `~/.openclaw/skills/`
- Skills installed (built-in): `~/homebase/code/openclaw/skills/`
- MemPalace: `~/.mempalace/palace` — long-term memory

## Reddit Ads

- Campaign map: `/home/amir/homebase/code/FIGHTCITYTICKETS-1/city-campaign-map.json`
- Budget skill: `~/.openclaw/skills/reddit-budget/`
- Rule: never mutate without campaign ID in map AND human approval

## Financial

- Stripe: ~-$0.06 (expected pre-revenue)
- Lob: ~$7.83 (below $15 alert — ~1 letter remaining at current pricing)

## Infrastructure

- Redis: Railway-managed (do not connect directly)
- GoDaddy DNS: parkingbreaker.com (ns27.domaincontrol.com)

## Jules

- Dashboard: jules.google.com
- API key: `/home/amir/homebase/code/inkspander/.env`
- Note: stash local changes before pulling Jules updates
