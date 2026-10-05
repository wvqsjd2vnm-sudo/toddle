import json
from datetime import date

from . import config, llm, scraper

EXTRACT_SYS = """You read raw text copied from a school's Toddle parent portal.
Extract two lists and return {"homework": [...], "announcements": [...]}.
homework: ONLY items that are homework / take-home assignments (not classwork, not general
notices). Each: {"subject","title","instructions","due_date","status"}.
announcements: school/teacher notices. Each: {"subject","title","text","date"}.
Do not invent anything not in the text."""

SOLVE_SYS = """You are a patient tutor preparing a worked DRAFT of a homework task for a child
({name}, {grade}). Give the full answer, but show the reasoning step by step in simple
language a 4th or 5th grader can read: short sentences, easy words, small steps, a quick "why" for each step. End with a one-line "Check yourself" question so the child can test that he understood. If the task
needs something you cannot see (a worksheet image, a book page, a physical activity), say
exactly what is missing instead of guessing."""

ASSESS_SYS = """From a school announcement, decide if it announces an assessment (test, quiz,
exam, unit assessment, dictation, oral, project submission). Return
{"is_assessment": bool, "subject": str, "date": str, "topics": [str]}."""

PREDICT_SYS = """You are a study coach for {name} ({grade}). Given an announced assessment and
the student's recent homework and announcements from Toddle, predict what the assessment
will most likely cover and how it will be set. Produce Markdown with: 1) Likely topics
(ranked, with the evidence from the homework/announcements), 2) Question types to expect,
3) A day-by-day study plan up to the assessment date, 4) 10 practice questions with an
answer key. Be explicit about confidence and what is a guess."""


PICK_SYS = """These are menu links from a school's Toddle parent/student portal. Choose the ones
most likely to contain homework / assignments / to-do items, announcements / notices /
messages, and the assessment/test calendar. Skip settings, profile, help, logout.
Return {"open": ["exact link text", ...]} (max 8)."""


def pick_pages(links: list[dict]) -> list[str]:
    res = llm.ask_json(PICK_SYS, json.dumps(links, ensure_ascii=False))
    return [t for t in (res.get("open", []) if isinstance(res, dict) else []) if isinstance(t, str)]


def run(headless: bool = True) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = scraper.fetch_pages(headless, pick=pick_pages)
    corpus = "\n\n".join(f"=== {k} ===\n{v}" for k, v in pages.items())
    config.OUT_DIR.joinpath("last-pages-seen.txt").write_text(corpus)  # debug: what the agent saw
    data = llm.ask_json(EXTRACT_SYS, corpus[:150_000], max_tokens=8000)
    homework = data.get("homework", []) if isinstance(data, dict) else []
    announcements = data.get("announcements", []) if isinstance(data, dict) else []
    today = date.today().isoformat()
    (config.OUT_DIR / f"{today}-raw.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # 1) Homework drafts
    sys_solve = SOLVE_SYS.format(name=config.STUDENT_NAME, grade=config.STUDENT_GRADE or "school-age")
    lines = [f"# Homework drafts – {today}\n",
             "_Drafts to review with your child. He should read, understand and write them in his own words._\n"]
    for hw in homework:
        lines.append(f"\n## {hw.get('subject','')}: {hw.get('title','')} (due {hw.get('due_date','?')})\n")
        lines.append(llm.ask(sys_solve, json.dumps(hw, ensure_ascii=False)))
    (config.OUT_DIR / f"{today}-homework.md").write_text("\n".join(lines))

    # 2) Assessment prediction
    context = json.dumps({"homework": homework, "announcements": announcements}, ensure_ascii=False)
    sys_predict = PREDICT_SYS.format(name=config.STUDENT_NAME, grade=config.STUDENT_GRADE or "school-age")
    out = [f"# Assessment predictions – {today}\n"]
    found = False
    for a in announcements:
        info = llm.ask_json(ASSESS_SYS, json.dumps(a, ensure_ascii=False))
        if isinstance(info, dict) and info.get("is_assessment"):
            found = True
            out.append(f"\n## {info.get('subject','')} – {info.get('date','date TBC')}\n")
            out.append(llm.ask(sys_predict, f"Assessment: {json.dumps(info)}\n\nContext: {context}", 6000))
    if not found:
        out.append("No assessment announcements found.")
    (config.OUT_DIR / f"{today}-assessments.md").write_text("\n".join(out))
    print(f"{len(homework)} homework items, results in {config.OUT_DIR}/")
