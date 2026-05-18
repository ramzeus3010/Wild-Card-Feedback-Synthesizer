# Claude Code Build Prompt — M6 Design Partner Synthesis Agent

You are building a working AI agent for a take-home assignment at Utopia Studio (Doha-based venture studio backed by Qatar Development Bank). This is for a real job application — Agentic Operator Internship, M6 Product & Technology track. Deadline: 3 days. Submission: GitHub repo + Loom video + 1-page writeup, all through Ashby.

The grading rubric explicitly weighs: problem framing, technical execution, output quality, speed/judgment (what was CUT), and diligence (honest writeup). Their explicit hint: "Fast thinkers make good cuts. Slow ones try to build everything."

---

## Rules you must follow throughout this build

1. **Do not add features I did not ask for.** No CLI flags, no logging frameworks, no progress bars, no `--verbose`, no `--model` argument, no config files, no Rich-styled output. If you think something is "nice to have," stop and ask before adding it.
2. **Keep `run.py` under 150 lines.** Readability over cleverness. No classes; helper functions are fine.
3. **Use the Anthropic Python SDK with tool use for structured output.** NOT "return JSON in your response" with string parsing. Force the model into the schema via a tool definition.
4. **The system prompt is the real craft work.** Spend effort there, not on CLI UX.
5. **Secrets:** All API keys go in `.env`. Commit `.env.example` (blank values). Never commit `.env`. `.gitignore` must include `.env`.
6. **When unsure between two valid approaches, default to the smaller/simpler one. Then ask me.**
7. **Comments are for non-obvious *why*, not for *what*.** Don't narrate code that speaks for itself.
8. **Use type hints in all Python.**
9. **Match Utopia's vocabulary** in all human-readable strings: "Fellow" (not "founder"), "Gate G4," "Kill Signal," "design partner," "studio operator," "co-build."
10. **Stop and check in after each major step** of the build order before proceeding to the next. Do not steamroll through all 8 steps in one go.
11. **Dependencies are exactly two:** `anthropic`, `python-dotenv`. Nothing else.
12. **Model:** `claude-sonnet-4-6`. Set as a constant at the top of `run.py`. Do not parameterize it.

---

## Context: what Utopia Studio is (background only — don't restate in code)

- Venture studio in Doha, backed by Qatar Development Bank
- Co-builds AI-native companies with domain expert "Fellows"
- 6-month program: 9 modules (M1–M9), 8 gates (G0–G8)
- Up to $1M per venture, target Series A in <12 months
- M6 is the Product & Technology module — runs 10–12 weeks, owns Gate G3 (product ready for paying customers) and Gate G4 (5 design partners onboarded with scorecard live)
- M6 is run by Ollie Graham-Yooll (CPO/COO) and Karan Pinto (CTO)
- Currently 4 live ventures: Evos, Mentix, Azraq, Barrier Intelligence + 8 stealth

## Context: the operator and the problem

- **Operator:** Ollie Graham-Yooll and Karan Pinto — they run M6
- **Their pain:** 6–10 Fellows are simultaneously onboarding design partners and collecting feedback. Each Fellow synthesizes that feedback in Claude chat ad-hoc, getting a different-shaped output every time. The studio can't compare across Fellows, can't standardize handoff to Linear, can't see which Fellow is approaching Gate G4 readiness.
- **What the agent does:** Takes 3–5 design partner feedback artifacts (call transcripts, written feedback, Slack messages) from one Fellow, returns a structured synthesis with consistent schema, Kill Signal flags, and Gate G4 readiness score.

## The four Kill Signals (Utopia's framework — must be embedded in the agent's system prompt)

1. **No data loop by G2** — venture can't explain how the AI gets smarter from being used. *Trigger examples:* feedback suggesting the product doesn't learn, doesn't adapt, doesn't improve with use.
2. **Model capability shock** — eval harness below 60% on what matters. *Trigger examples:* feedback that core AI capability is fundamentally insufficient for the use case.
3. **No AI moat by G3** — moat ledger has fewer than 2 durable reasons the venture can't be copied. *Trigger examples:* "I could build this with ChatGPT," "what makes this different from X."
4. **Accuracy below the safety floor** — error rate past the line drawn. *Trigger examples:* feedback about wrong answers, hallucinations, inconsistent outputs across identical inputs.

---

## File structure (build exactly this)

```
m6-design-partner-synthesis/
├── README.md
├── SKILL.md
├── prompts/
│   └── system_prompt.md
├── schemas/
│   └── output_schema.json
├── examples/
│   ├── input_eterna_1.txt
│   ├── input_eterna_2.txt
│   ├── input_eterna_3.txt
│   ├── input_eterna_4.txt
│   ├── input_eterna_5.txt
│   ├── output_eterna.json
│   └── output_eterna.md
├── inputs/
│   └── .gitkeep
├── outputs/
│   └── .gitkeep
├── archive/
│   └── .gitkeep
├── run.py
├── requirements.txt
├── .env.example
└── .gitignore
```

### `.gitignore` contents:
```
.env
.venv/
__pycache__/
*.pyc
.DS_Store
inputs/*
!inputs/.gitkeep
outputs/*
!outputs/.gitkeep
archive/*
!archive/.gitkeep
```

### `.env.example` contents:
```
ANTHROPIC_API_KEY=
```

### `requirements.txt` contents:
```
anthropic>=0.40.0
python-dotenv>=1.0.0
```

---

## Build order — check in with me after each step

### Step 1: Scaffold

Create the directory tree, all empty placeholder files (`.gitkeep` for the three runtime folders), `.gitignore`, `.env.example`, `requirements.txt`. Confirm `pip install -r requirements.txt` works in a fresh venv. **Check in.**

### Step 2: Output schema

Create `schemas/output_schema.json` — a JSON Schema document with the following structure. Use proper JSON Schema syntax (`type`, `properties`, `required`, `items`, etc.) so it can be passed directly into an Anthropic tool definition.

Fields:

- `fellow_id` (string, required) — Fellow name or product name
- `synthesis_date` (string, ISO 8601 date, required)
- `design_partners_synthesized` (integer 1–10, required)
- `themes` (array, max 3 items, required) — each item has:
  - `theme` (string, short title)
  - `summary` (string, 1–2 sentences)
  - `partners_raising` (array of strings — partner identifiers)
  - `severity` (enum: `"blocker" | "major" | "minor"`)
- `critical_objections` (array, required, can be empty) — each item has:
  - `objection` (string, 1 sentence)
  - `partner_source` (string)
  - `blocks_paying` (boolean)
- `must_fix_for_g4` (array of strings, min 1 item, required) — 1-sentence items
- `nice_to_have_post_launch` (array of strings, required, can be empty)
- `next_sprint_brief` (string, required) — one paragraph, 3–5 sentences, Fellow-facing
- `kill_signal_flags` (array, required, can be empty) — each item has:
  - `signal` (enum: `"data_loop" | "model_capability" | "ai_moat" | "accuracy_floor"`)
  - `triggered_by` (string — exact quote or paraphrase from input)
  - `rationale` (string, 1 sentence)
- `g4_readiness_score` (integer 1–10, required)
- `g4_readiness_rationale` (string, 1–2 sentences, required)

**Check in** — show me the full JSON Schema before moving on.

### Step 3: The 5 Eterna feedback transcripts

Eterna is an AI journaling app — users record voice memos, the app turns them into structured memory entries searchable by people/places/themes/dates. Live on App Store. Built by Ramazan (the candidate). The agent is being tested on feedback for Ramazan's own product as the demo.

Write 5 transcripts in `examples/input_eterna_*.txt`. Each is a different design partner with a different persona. **Two must contain content that should trigger Kill Signal flags. One should be deliberately too short for the agent to draw conclusions from.** Length: 200–400 words each except where noted.

- **input_eterna_1.txt — The Love Letter.** 34-year-old new dad. Uses Eterna daily for 6 weeks. Wants to send memory capsules to his wife as a Mother's Day gift. Gushing but specific (must mention concrete app features like voice capture, people-tagging, the search). Already pays, would pay more.
- **input_eterna_2.txt — The Skeptic.** Product manager at a tech company. Tried it 2 weeks. Useful but unconvinced. **Must include a line equivalent to "Honestly, I could probably build 80% of this with ChatGPT and a Notion template."** → triggers Kill Signal `ai_moat`. Won't pay yet.
- **input_eterna_3.txt — The Confused User.** 58-year-old retired teacher who got the app from her daughter. Doesn't know what to record. Wishes the app prompted her. **Must include sentiment that after 3 weeks the app doesn't feel like it "knows her" any better than day one.** → triggers Kill Signal `data_loop`. Stopped using it after week 2.
- **input_eterna_4.txt — The Technical Tester.** 28-year-old indie iOS developer. Power user. **Must include the observation that the same voice memo, when re-imported, produced two different memory summaries with conflicting tags/dates.** → triggers Kill Signal `accuracy_floor`. Curious but won't recommend until reliable.
- **input_eterna_5.txt — The Quiet One.** 41-year-old therapist. Just 2–3 sentences total. "Yeah it's nice. Used it a few times. The mic cut out once." Vague. The agent should recognize this is insufficient data and say so in the synthesis.

Format each transcript as if it were pasted into a Slack message or feedback form — natural language, not over-polished. Include partner name and one identifying line at the top of each file.

**Check in** — show me one transcript fully drafted before writing the other four.

### Step 4: The system prompt — `prompts/system_prompt.md`

This is the core craft work. Target ~600–900 words. Structure:

1. **Role.** "You are the M6 Design Partner Synthesis Agent for Utopia Studio. You serve studio operators (Ollie Graham-Yooll, Karan Pinto) and the Fellows running ventures in the M6 Product & Technology module."
2. **What Utopia is** — one paragraph of context (venture studio, AI-native, co-build with Fellows, gates G0–G8). Enough to ground voice and vocabulary; no more.
3. **What Gate G4 means** — 5 design partners onboarded with a scorecard live. Fellow must show product works for real users who would pay. Be concrete about what "scorecard live" implies.
4. **The four Kill Signals** — define each with example triggers. Tell the model to flag any signal it sees evidence for, with exact quote or paraphrase plus 1-sentence rationale. Do not over-flag — only flag when there's a clear textual basis.
5. **Tone for human-readable strings** (`next_sprint_brief`, theme summaries, rationales) — direct, builder-to-operator, no corporate fluff. Match how Ollie/Karan would talk: short sentences, real verbs, no "leverage," no "synergy," no "unlock," no "best-in-class."
6. **Strict instructions:**
   - Output must match the provided tool schema exactly.
   - Themes: top 3 only, ranked by what matters most for G4 readiness.
   - Be honest about insufficient data. If a partner gave 2 sentences, say so in the synthesis. Do not fabricate inference. Note them in the rationale, do not pad themes with their vagueness.
   - The `next_sprint_brief` is what the Fellow reads first thing Monday morning. It must be useful, specific, and not generic.
7. **G4 readiness score guidance:**
   - 1–3: not close, fundamental issues across multiple partners
   - 4–6: building toward G4 with specific identified blockers
   - 7–8: ready or near-ready, minor polish remaining
   - 9–10: clear go (rare; requires strong signal across multiple partners including stated willingness to pay)
8. **Final instruction:** Always call the `synthesize_feedback` tool. Never respond in free text.

**Check in** — show me the full draft. The system prompt is where I want to spend iteration cycles.

### Step 5: `run.py` — the harness

Behavior, in this order:

1. Load `.env`, init `Anthropic` client. Error clearly if `ANTHROPIC_API_KEY` missing.
2. Read all `.txt` and `.md` files in `inputs/`. Error out cleanly if folder is empty.
3. Concatenate input contents into a single user message, each file labeled with its filename as a header (`### {filename}\n{content}`).
4. Load system prompt from `prompts/system_prompt.md`.
5. Load output schema from `schemas/output_schema.json` and wrap it as a tool definition (`name: synthesize_feedback`, `description: ...`, `input_schema: <the JSON Schema>`).
6. Call Claude with `tool_choice={"type": "tool", "name": "synthesize_feedback"}` to force structured output. Model = `claude-sonnet-4-6`. `max_tokens=4096`.
7. One retry on `APIError`. After second failure, surface the error and exit non-zero.
8. Parse the tool input from the response — that's the synthesis dict.
9. Write `outputs/synthesis.json` (pretty-printed, UTF-8, indent=2).
10. Generate `outputs/synthesis.md` — Slack-formatted human-readable version (format below).
11. Print the Markdown version to terminal so the operator sees it immediately.
12. Archive: create `archive/{ISO_timestamp}/` (use `YYYY-MM-DDTHH-MM-SS` format — colons break on some filesystems). Move all input files from `inputs/` into it. Copy both output files into it. After archive, `inputs/` is empty again, `outputs/` contains the latest run.

**`synthesis.md` format (Slack-ready Markdown):**

```
*M6 Design Partner Synthesis — {fellow_id}*
_{synthesis_date} · {design_partners_synthesized} partners synthesized_

*Gate G4 Readiness:* {g4_readiness_score}/10
> {g4_readiness_rationale}

*Top Themes*
1. *{theme}* _({severity})_ — {summary}
   Raised by: {comma-joined partners_raising}
2. ...

*Critical Objections*
- {objection} — _{partner_source}_ {🛑 if blocks_paying else ""}
(or "None raised." if empty)

*Must-fix for Gate G4*
- {item}

*Nice-to-have (post-launch)*
- {item}
(or "None flagged." if empty)

*Kill Signal Flags*
(if empty: "None triggered.")
- ⚠️ *{signal}* — {rationale}
  _Triggered by:_ "{triggered_by}"

*Next Sprint Brief*
{next_sprint_brief}
```

Use small helper functions: `load_inputs()`, `build_tool_definition()`, `call_claude()`, `format_slack_markdown()`, `archive_run()`. No classes. Use `pathlib.Path` everywhere, not `os.path`. Use `datetime.datetime.now(datetime.UTC)` for the archive timestamp. UTF-8 on all file I/O.

**Check in** — show me the full `run.py` before testing it end-to-end.

### Step 6: `SKILL.md`

Follow Anthropic's Agent Skills format: YAML frontmatter (`name`, `description`) followed by markdown body with instructions for an agent loading this skill.

Frontmatter:
- `name: m6-design-partner-synthesis`
- `description: Synthesizes 3–5 design partner feedback artifacts into a structured Gate G4 readiness report with Kill Signal flags, for M6 Fellows and studio operators at Utopia Studio.`

Body sections: When to use, Inputs expected, Outputs produced, Utopia Studio context (Gate G4 + four Kill Signals briefly), How to invoke (the `run.py` workflow).

Keep it under 1 page. This file is the "open marketplace" handle for the skill — concise and self-contained.

### Step 7: `README.md`

Sections in this order:

1. **Title + one-line description**
2. **The problem** (3–4 sentences, operator-focused, use Utopia vocabulary)
3. **The agent** (3–4 sentences: what it does, input, output, which tool/API it actually calls)
4. **Setup** (4 commands):
   ```
   git clone ...
   pip install -r requirements.txt
   cp .env.example .env
   # paste your ANTHROPIC_API_KEY into .env
   ```
5. **Usage** (drop feedback files in `inputs/`, run `python run.py`, find outputs in `outputs/`, history in `archive/`)
6. **File structure** (the tree, briefly annotated)
7. **Example run** — point at `examples/output_eterna.json` and `examples/output_eterna.md` as a pre-computed sample so reviewers can see output without running.
8. **Prompts used** — embed or link `prompts/system_prompt.md`
9. **APIs called** — Anthropic Messages API with forced tool use for structured output
10. **Limitations & what broke** — leave a placeholder section header (`<!-- TO FILL AFTER TESTING -->`) for me to write
11. **What I cut** — leave a placeholder section header for me to write

### Step 8: End-to-end run

Copy the 5 example transcripts from `examples/` into `inputs/` and run `python run.py`. Verify:

- Output JSON validates against the schema
- At minimum 2 of the 3 expected Kill Signals fire (`ai_moat` from input_2, `accuracy_floor` from input_4, `data_loop` from input_3)
- G4 readiness score falls in 3–6 range (mixed feedback should not score 7+)
- The Quiet One (input_5) is explicitly acknowledged as insufficient data
- The Slack Markdown renders cleanly when pasted (no broken formatting)
- `inputs/` is empty after the run; `archive/{timestamp}/` contains 7 files (5 inputs + 2 outputs); `outputs/` has the 2 outputs

Save the produced JSON and Markdown to `examples/output_eterna.json` and `examples/output_eterna.md` so the repo ships with a pre-computed sample.

---

## Things you should NOT build (explicit cuts — these go in the writeup as judgment signal)

- No Slack bot interface
- No scheduled/automated runs
- No second-agent handoff (Linear ticket creation, etc.)
- No web UI, no Streamlit, no dashboard
- No real Granola/Slack/Linear API integration — Claude API is the *one* real integration
- No `argparse` CLI options
- No `logging` framework — `print()` is fine for the terminal echo
- No unit tests — manual end-to-end run is the test
- No Docker, no CI, no GitHub Actions
- No `pyproject.toml` — `requirements.txt` only

---

## Coding standards

- Python 3.10+
- Type hints on all function signatures
- `from __future__ import annotations` at the top of `run.py`
- `pathlib.Path` only, never `os.path`
- `datetime.datetime.now(datetime.UTC)` for timestamps
- UTF-8 file I/O explicit (`encoding="utf-8"`)
- f-strings, not `.format()` or `%`
- Dependencies exactly two: `anthropic`, `python-dotenv`

---

## Acceptance criteria

- `python run.py` runs end-to-end on the 5 example inputs without error
- Output JSON validates against `schemas/output_schema.json`
- Slack Markdown is produced and printed to terminal
- Archive contains the run with timestamp
- `inputs/` is empty after the run
- `run.py` is under 150 lines
- README has all 11 sections
- `.env` is gitignored, `.env.example` is committed

## When you're done

Tell me: what you built, what you skipped, what surprised you, and any places where you made a judgment call between two valid approaches. Do not claim done until the end-to-end run completes successfully and the example outputs are saved.

**Start with Step 1. Check in after each step.**
