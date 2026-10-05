# Toddle homework & assessment agent

Reads your son's **homework** (only) and **announcements** from Toddle, then writes to `out/`:

- `YYYY-MM-DD-homework.md` – step-by-step worked drafts for every homework item, all subjects
- `YYYY-MM-DD-assessments.md` – for each announced assessment: predicted topics, question types, a study plan and practice questions with answers

## Setup (run on your own computer)
```bash
pip install -r requirements.txt && playwright install chromium
export ANTHROPIC_API_KEY=...        # your key
export STUDENT_NAME="Ahmed" STUDENT_GRADE="Grade 5"
python -m toddle_agent login        # log in yourself once (OTP/Google OK); no password is stored
python -m toddle_agent run          # run any time, or schedule daily with cron
```
Optional: `TODDLE_URL`; `CHROMIUM_PATH` (use an existing Chromium); `TODDLE_PAGES` (e.g. `/assignments,/announcements`) to skip auto-discovery.

## How it finds the pages
After login it reads Toddle's menu, asks Claude which links hold homework, announcements and assessments, opens them, and extracts only the homework. `out/last-pages-seen.txt` shows exactly what the agent saw, so if the result looks wrong you can see why.

## Notes
- The agent **does not submit** anything to Toddle. It prepares drafts so your son can learn from them and hand in his own work.
- Explanations are written at a 4th–5th grade reading level so your son can understand and redo them himself. They are not styled to imitate a child's writing.
- Page text is read generically (no fragile selectors), but it hasn't been tested against your school's live Toddle account – if the output is empty, check `out/last-pages-seen.txt`, run with `--show`, or set `TODDLE_PAGES`.
