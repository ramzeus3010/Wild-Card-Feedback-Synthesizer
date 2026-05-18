---
name: m6-design-partner-synthesis
description: Synthesizes 3–5 design partner feedback artifacts into a structured Gate G4 readiness report with Kill Signal flags, for M6 Fellows and studio operators at Utopia Studio.
---

## When to use
Invoke this skill when a Fellow has collected 3–5 design partner feedback artifacts and needs them turned into a single structured synthesis the studio can compare across ventures. Use it whenever the question is "is this Fellow getting close to Gate G4?" — not for one-off feedback triage on a single message.

## Inputs expected
Drop 3–5 feedback artifacts into `inputs/` as `.txt` or `.md` files. Any medium works — Slack messages, Zoom auto-transcripts, in-app feedback forms, emails, iMessage / WhatsApp threads, plain notes. Use the filename convention `{PartnerName}_{medium}.txt` (e.g. `Daniel_slack.txt`, `Priya_zoom.txt`) so the agent has a soft hint about partner identity and source. If the filename doesn't follow that shape, the agent will infer from the content.

## Outputs produced
Two files in `outputs/`, also copied into `archive/{timestamp}/` for history:

- `synthesis.json` — structured payload conforming to `schemas/output_schema.json`: `fellow_id`, `synthesis_date`, `design_partners_synthesized`, top 3 `themes` (with severity), `critical_objections`, `must_fix_for_g4`, `nice_to_have_post_launch`, `next_sprint_brief`, `kill_signal_flags`, `g4_readiness_score` (1–10), `g4_readiness_rationale`.
- `synthesis.md` — Slack-ready human-readable version of the same payload, also echoed to the terminal.

The original input files are moved into `archive/{timestamp}/`, leaving `inputs/` empty for the next run.

## Utopia Studio context
Utopia is a Doha-based venture studio that co-builds AI-native companies with domain expert Fellows. M6 is the Product & Technology module. **Gate G4** is the milestone where a venture has 5 design partners onboarded with a scorecard live — real partner usage on real metrics, not vibes. The synthesis flags evidence of any of Utopia's four **Kill Signals**:

- `data_loop` — product doesn't get smarter from being used
- `model_capability` — underlying AI capability is fundamentally insufficient for the use case
- `ai_moat` — fewer than 2 durable reasons the venture can't be copied
- `accuracy_floor` — error rate past the line drawn

Flags require a direct quote or close paraphrase from the input; the agent will not flag on tone alone.

## How to invoke

```bash
# one-time setup
pip install -r requirements.txt
cp .env.example .env   # then paste ANTHROPIC_API_KEY into .env

# every run
# 1. drop 3–5 feedback files into inputs/
# 2. run:
python run.py
# 3. read outputs/synthesis.md (also printed to terminal); JSON sits alongside
```

The agent uses the Anthropic Messages API with forced tool use (`synthesize_feedback`) to guarantee schema-conformant output. Model: `claude-sonnet-4-6`.
