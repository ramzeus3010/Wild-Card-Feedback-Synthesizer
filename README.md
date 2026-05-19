# M6 Design Partner Synthesis Agent

Turns 3–5 design partner feedback artifacts and an optional weekly scorecard from one Fellow into a structured Gate G4 readiness report with Kill Signal flags — then routes the result to the next agent in Utopia OS.

## The problem

Inside M6, 6–10 Fellows are simultaneously onboarding design partners and collecting feedback — Slack threads, Zoom transcripts, in-app forms, emails, the occasional iMessage. Each Fellow synthesizes that feedback ad-hoc in Claude chat, getting a different-shaped output every time. The studio can't compare across Fellows, can't standardize the handoff into Linear, and can't see at a glance which Fellow is approaching Gate G4 readiness or which one is about to hit a Kill Signal. This agent fixes the shape problem so the operator's view of the cohort is comparable, not anecdotal — and routes the synthesis into the right next-step action without a human in the middle.

## The agent

Two agents wired into one pipeline, fired from a single command.

**Synthesis agent (`run.py`).** Drops 3–5 design partner feedback files into `inputs/`, optionally a `scorecard.*` file, and runs. Calls the Anthropic Messages API with forced tool use against `schemas/output_schema.json` — the model is constrained to the exact schema by construction, not by string parsing. Produces two files in `outputs/`: a structured `synthesis.json` and a Slack-ready `synthesis.md`.

**Routing agent (`route.py`).** Fires automatically after synthesis. Reads `synthesis.json` and branches deterministically:

- Kill Signals fired OR score ≤ 3 → `escalation.md` — Slack-ready draft for Ollie/Karan
- No Kill Signals, score 4–7 → `linear_tickets.json` — Linear API-shaped issue payloads
- No Kill Signals, score 8+ → `g4_ready_brief.md` — handoff brief to M7 Go-to-Market

Routing logic is deterministic Python; only the *content* inside the handoff file is LLM-generated. `route.py` is also independently runnable on an existing synthesis if you want to re-route without re-synthesizing.

## Setup

```bash
git clone <this-repo-url>
cd <repo>
pip install -r requirements.txt
cp .env.example .env
# paste your ANTHROPIC_API_KEY into .env
```

## Usage

1. Drop 3–5 feedback artifacts into `inputs/` as `.txt` or `.md` files. Rename using `{PartnerName}_{medium}.txt` — e.g. `daniel_slack.txt`, `priya_zoom.txt`, `margaret_form.txt`. The filename is a soft hint to the agent; if you skip the convention it will infer partner and medium from the content.
2. *(Optional)* Drop a scorecard file into `inputs/`. Any file whose name starts with `scorecard` (case-insensitive) is treated as the venture's weekly scorecard rather than partner feedback. Format-agnostic: Markdown, JSON, CSV, or copy-pasted PostHog dashboard all work. The agent extracts what's there, doesn't assume a schema.
3. Run:

   ```bash
   python run.py
   ```

4. Read `outputs/synthesis.md` (also printed to the terminal). The structured payload is in `outputs/synthesis.json` next to it. The routing agent fires automatically and writes one of three handoff files to `outputs/` depending on the synthesis: `escalation.md`, `linear_tickets.json`, or `g4_ready_brief.md`.
5. Past runs live under `archive/{ISO-timestamp}/` — each contains the original inputs plus all generated outputs from that run, kept together so the synthesis and its routed handoff are one bundle.

After a successful run, `inputs/` is empty, `outputs/` holds the latest run, and the archive has the full bundle.

## File structure

```
.
├── README.md                          this file
├── SKILL.md                           Anthropic Agent Skill handle (one-page)
├── run.py                             synthesis harness + pipeline orchestrator
├── route.py                           routing agent (second node in Utopia OS)
├── requirements.txt                   anthropic, python-dotenv
├── .env.example                       commit; .env is gitignored
├── prompts/
│   ├── system_prompt.md               synthesis prompt — the real craft work
│   └── route_system_prompt.md         routing prompt (escalation / tickets / brief)
├── schemas/
│   ├── output_schema.json             synthesis output schema (tool input_schema)
│   └── linear_tickets_schema.json     Linear issueCreate-shaped tool schema
├── examples/
│   ├── aris_email.txt                 5 Eterna partner artifacts, varied media:
│   ├── chloe_whatsapp.txt             email, WhatsApp, Slack, Google Form, audio
│   ├── david_slack.txt
│   ├── Jordan_googleform.txt
│   ├── maya_audio.txt
│   ├── scorecard_eterna.md            example weekly scorecard
│   ├── output_synthesis.json          pre-computed sample run (structured)
│   ├── output_synthesis.md            pre-computed sample run (Slack-ready)
│   └── output_linear_tickets.json     pre-computed routed handoff
├── inputs/                            drop feedback files here (gitignored except .gitkeep)
├── outputs/                           latest run lands here (gitignored except .gitkeep)
└── archive/                           past runs by ISO timestamp (gitignored except .gitkeep)
```

## Example run

The repo ships with a pre-computed sample run based on the 5 Eterna design partner artifacts and a strong weekly scorecard. This particular run scored 7/10 — no Kill Signals fired, but the agent flagged universally positive feedback as a yellow flag worth investigating — so the routing agent fired the **tickets** branch:

- [`examples/output_synthesis.md`](examples/output_synthesis.md) — Slack-ready synthesis
- [`examples/output_synthesis.json`](examples/output_synthesis.json) — same payload, structured
- [`examples/output_linear_tickets.json`](examples/output_linear_tickets.json) — Linear-API-shaped tickets from the routing agent

You can read these without running anything. The five sample inputs (`aris_email.txt`, `chloe_whatsapp.txt`, `david_slack.txt`, `Jordan_googleform.txt`, `maya_audio.txt`) cover varied media to exercise format-agnostic ingestion. The scorecard (`scorecard_eterna.md`) follows the Utopia framework: one master metric (D30 retention), supporting metrics, per-partner cohort breakdown, stated willingness-to-pay.

## Prompts used

Two system prompts, both in `prompts/`:

- [`prompts/system_prompt.md`](prompts/system_prompt.md) — synthesis agent. Covers role, Utopia context, Gate G4 definition, the four Kill Signals with trigger criteria, scorecard handling (master metric, supporting metrics, trend direction, cohort coverage), severity definitions, tone, and the G4 readiness score rubric.
- [`prompts/route_system_prompt.md`](prompts/route_system_prompt.md) — routing agent. Covers the three handoff modes (escalation, tickets, ready brief), studio voice, and per-mode content guidance.

The prompts are where iteration cycles go. `run.py` and `route.py` are intentionally boring plumbing.

## APIs called

One real integration: the Anthropic Messages API. Both agents use it.

- Model: `claude-sonnet-4-6`
- Synthesis: `tools=[{name: "synthesize_feedback", input_schema: <output_schema>}]` with forced tool use — schema-conformant by construction, no string parsing.
- Routing (tickets branch): `tools=[{name: "generate_tickets", input_schema: <linear_tickets_schema>}]` with forced tool use.
- Routing (escalation / ready brief branches): regular text completion — the output is a Markdown document, not structured data.
- One retry on `APIError`, then exit non-zero. If routing fails, synthesis is still preserved and archived; the routing error is surfaced clearly.

No Slack / Granola / Linear / Notion integrations called directly. The outputs are *shaped* as their API payloads, but the actual API calls are explicit out-of-scope (see "What I cut").

## Limitations & what broke

- **Schemas constrain syntax, not meaning.** I assumed defining `severity` as an enum (`blocker | major | minor`) would teach the model what each value meant. It didn't — the model was filling in "blocker" from general training intuition, which is why universally positive feedback got flagged `blocker` severity in the all-positive stress test. Fix: added explicit definitions tying each severity level to Utopia's G4 framing in the system prompt. The lesson generalizes — schemas and prompts do different jobs, and both need to be deliberate.
- **First end-to-end `route.py` run errored on the tickets branch.** A string-formatting bug while building the user message for ticket generation. The fix took five minutes; the more useful finding was that the error-isolation logic in `run.py` worked as designed — synthesis was preserved and archived, the failure was surfaced clearly rather than silently rolling back the whole pipeline. Would not have caught that the protection worked without the failure.
- **Inputs are plain text and markdown only — no native `.docx` / `.pdf` parsing.** Real Fellow inputs will be messier — bundled WhatsApp screenshots, Granola transcripts, Slack thread copies. Held to plain formats to keep dependencies minimal. The right fix is Anthropic's native document blocks plus a Granola pull — neither changes synthesis quality, only ingestion friction.

## What I cut

- **Slack and Linear poster agents.** The agent's outputs are already shaped as the exact API payloads each destination needs — `escalation.md` is the Slack message body, `linear_tickets.json` matches Linear's `issueCreate` schema field-for-field. Building the posters is mechanical (~20–30 lines per agent) and explicitly out of scope to stay focused on judgment, not integration breadth. The contract is the file; the integration is mechanical.
- **Predefined scorecard schema.** The agent treats scorecard data as format-agnostic input rather than defining its shape, because I don't have visibility into how Utopia structures scorecards internally. Defining one would risk faking domain expertise. The system prompt instead instructs the model to look for a master metric, supporting metrics, trend direction, and cohort coverage across any shape of input. Once exposed to real ones, the next iteration tightens the parser around your conventions.
- **CLI ergonomics and a web UI.** No argparse flags, no Streamlit dashboard, no fancy logging. Folder-in / folder-out with terminal output is the smallest interface that still feels like an operator tool. Anything more is developer ego, not operator instinct.
