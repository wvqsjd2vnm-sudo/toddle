# Games hub with one-time codes

Each of the 100 player codes works **once**. The first person to enter a code gets in (and stays in on
that browser); anyone else using the same code sees "This code was already used." The Worker marks the
code USED in its database instantly and atomically. Game files (`f1`, `storm`) are only served to
browsers that redeemed a code, so the direct links can't be used to skip the code screen.

```
site/            the hub (index.html), admin.html, games, status.json   (from "games-hub 3")
src/worker.js    redeem / session / admin API + game gating
migrations/      database tables
scripts/codes_doc.py   load codes from the .docx, and mark USED codes back into the .docx
.claude/agents/code-keeper.md   Claude agent that reports/syncs code status
```

## Deploy (once, ~5 min, needs a free Cloudflare account)
```
npm install
npx wrangler login
npx wrangler d1 create games-codes          # paste the database_id into wrangler.toml
npx wrangler secret put ADMIN_CODE          # your admin code
npx wrangler secret put SESSION_SECRET      # any long random text
npx wrangler d1 migrations apply games-codes --remote
python3 scripts/codes_doc.py seed "CODES & GAME LINK.docx" > seed.sql
npx wrangler d1 execute games-codes --remote --file=seed.sql
npx wrangler deploy
```
Keep the Worker name `games` and your existing `games.play26.workers.dev` link keeps working.

## Day to day
- `/admin.html` -> type admin code -> see all codes, USED/unused, who you gave each to, Reset button.
- Mark used codes in your doc: `python3 scripts/codes_doc.py sync "CODES & GAME LINK.docx" https://games.play26.workers.dev ADMINCODE -o "CODES (updated).docx"`
  (or ask the `code-keeper` agent in Claude Code to do it).
- Maintenance mode / versions work as before (edit `site/status.json`, then `npx wrangler deploy`).

## Notes
- Local test: put `ADMIN_CODE` and `SESSION_SECRET` in `.dev.vars`, then `npx wrangler dev`.
- 10 wrong guesses per IP per 10 minutes, then blocked, so codes can't be guessed.
- A customer who clears their browser data or switches device loses access; use Reset for that code.
- The VR code is unchanged (it decrypts `vr.bin`); the one-time rule applies to the 100 player codes.
