# Taiwan Stock Dashboard V5 Data Architecture

This document defines the single supported automated data architecture.

## Independent modules

1. Stock quotes
   - Workflow: `.github/workflows/update-stocks.yml`
   - Script: `scripts/update_stocks.py`
   - Owns: `stocks.json`, `stock_history.json`

2. Stock OHLCV history
   - Workflow: `.github/workflows/update-stock-history.yml`
   - Script: `scripts/backfill_tracked_history.py`
   - Owns: `stock_ohlcv.json`

3. Put/Call ratio
   - Workflow: `.github/workflows/update-pc-ratio.yml`
   - Script: `scripts/fix_pc_ratio.py`
   - Owns the P/C fields inside `market.json` and `market_history.json` only.

4. Market core
   - Workflow: `.github/workflows/update-market.yml`
   - Script: `scripts/update_market.py`
   - Owns market core fields and CNN Fear & Greed data.
   - Must preserve P/C fields written by the P/C module.

5. Corporate actions / company events
   - Workflow: `.github/workflows/update-corporate-actions.yml`
   - Script: `scripts/update_corporate_actions.py`
   - Owns: `corporate_actions.json`, `company_events.json`

## Rules

- One module failing must not block any other module.
- Scheduled workflows must only update files owned by that module.
- Legacy `fix-*`, `patch-*`, `inject-*`, and one-off migration workflows are not part of the automated production path.
- Legacy workflows may remain in the repository for audit/history, but should not contain schedules.
- All scheduled workflows support `workflow_dispatch` for manual recovery.
- Data commits pull/rebase before push to reduce collisions between independent jobs.

## Taiwan schedule

- Corporate actions: 08:20 and 14:20 weekdays.
- Stock quotes: 14:45 weekdays.
- P/C ratio: 16:20, 17:20, 18:30 and 20:00 weekdays.
- Stock OHLCV history: 16:40 weekdays.
- Market core: 18:40 weekdays, plus 06:15 weekdays for night-session fields.

The schedules are intentionally staggered to avoid simultaneous commits to the repository.
