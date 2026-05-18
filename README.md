# M6 Design Partner Synthesis Agent

Turns 3–5 design partner feedback artifacts from one Fellow into a structured Gate G4 readiness report, with Kill Signal flags, in the same shape every time.

## The problem

Inside M6, 6–10 Fellows are simultaneously onboarding design partners and collecting feedback — Slack threads, Zoom transcripts, in-app forms, emails, the occasional iMessage. Each Fellow synthesizes that feedback ad-hoc in Claude chat, getting a different-shaped output every time. The studio can't compare across Fellows, can't standardize the handoff into Linear, and can't see at a glance which Fellow is approaching Gate G4 readiness or which one is about to hit a Kill Signal. This agent fixes the shape problem so the operator's view of the cohort is comparable, not anecdotal.

## The agent

You drop 3–5 design partner feedback files (any medium, any format) into `inputs/` and run `python run.py`. The agent uses the Anthropic Messages API with forced tool use to call a single tool — `synthesize_feedback` — whose `input_schema` is `schemas/output_schema.json`. That forces the model into the exact schema instead of relying on "return JSON" string parsing. You get back two files in `outputs/`: a structured `synthesis.json` and a Slack-ready `synthesis.md` echoed to the terminal.

## Setup

```bash
git clone <this-repo-url>
cd <repo>
pip install -r requirements.txt
cp .env.example .env
# paste your ANTHROPIC_API_KEY into .env
```

## Usage

1. Drop 3–5 feedback artifacts into `inputs/` as `.txt` or `.md` files.
2. Rename each file using the convention `{PartnerName}_{medium}.txt` — e.g. `Daniel_slack.txt`, `Priya_zoom.txt`, `Margaret_form.txt`, `Alex_email.txt`, `Reema_imessage.txt`. The filename is a soft hint to the agent; if you skip the convention it will infer partner and medium from the content.
3. Run:

   ```bash
   python run.py
   ```

4. Read `outputs/synthesis.md` (also printed to the terminal). The structured payload is in `outputs/synthesis.json` next to it.
5. Past runs live under `archive/{ISO-timestamp}/` — each contains the original input files plus both output files.

After a successful run, `inputs/` is empty (its files were moved into the archive), `outputs/` holds the latest run, and on the **next** run the leftover outputs are cleared automatically (drop if a twin exists in the latest archive, move there if not).

## File structure

```
.
├── README.md                  this file
├── SKILL.md                   Anthropic Agent Skill handle (one-page)
├── run.py                     harness (<150 lines)
├── requirements.txt           anthropic, python-dotenv
├── .env.example               commit; .env is gitignored
├── prompts/
│   └── system_prompt.md       the actual craft work
├── schemas/
│   └── output_schema.json     JSON Schema, used directly as the tool's input_schema
├── examples/
│   ├── input_eterna_1..5.txt  5 Eterna design partner artifacts, varied media
│   ├── output_eterna.json     pre-computed sample run (structured)
│   └── output_eterna.md       pre-computed sample run (Slack-ready)
├── inputs/                    drop feedback files here (gitignored except .gitkeep)
├── outputs/                   latest run lands here (gitignored except .gitkeep)
└── archive/                   past runs by ISO timestamp (gitignored except .gitkeep)
```

## Example run

You can see what the agent produces without running it. The repo ships with a pre-computed sample synthesis based on the 5 Eterna design partner artifacts in `examples/input_eterna_1..5.txt`:

- [`examples/output_eterna.md`](examples/output_eterna.md) — the Slack-ready synthesis
- [`examples/output_eterna.json`](examples/output_eterna.json) — the same payload, structured

The 5 sample inputs deliberately exercise media variety (Slack DM, Zoom transcript, in-app form, email, iMessage) and Kill Signal coverage (two of the four signals should fire from the content; one input is intentionally too thin to draw conclusions from).

## Prompts used

The system prompt is in [`prompts/system_prompt.md`](prompts/system_prompt.md). It covers role, Utopia context, what Gate G4 means, the four Kill Signals with trigger criteria, tone for the human-readable fields, strict instructions, and the G4 readiness score rubric. That file is where iteration cycles go — `run.py` is intentionally boring plumbing.

## APIs called

One real integration: the Anthropic Messages API.

- Model: `claude-sonnet-4-6`
- `max_tokens=4096`
- `tools=[{name: "synthesize_feedback", input_schema: <JSON Schema>}]`
- `tool_choice={"type": "tool", "name": "synthesize_feedback"}` — forces the model to call the tool, which makes the output schema-conformant by construction (no string parsing)
- One retry on `APIError`, then exit non-zero

No Slack / Granola / Linear / Notion integrations. Inputs are local files; outputs are local files.

## Limitations & what broke

<!-- TO FILL AFTER TESTING -->

## What I cut

<!-- TO FILL AFTER TESTING -->
