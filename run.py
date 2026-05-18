from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
from pathlib import Path

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

import route

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
TOOL_NAME = "synthesize_feedback"

ROOT = Path(__file__).parent
INPUTS_DIR = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
ARCHIVE_DIR = ROOT / "archive"
PROMPT_PATH = ROOT / "prompts" / "system_prompt.md"
SCHEMA_PATH = ROOT / "schemas" / "output_schema.json"


def load_inputs() -> tuple[str, str | None, list[Path]]:
    candidates = sorted(
        p for p in INPUTS_DIR.iterdir()
        if p.is_file() and p.name != ".gitkeep"
    )
    scorecard_files = [p for p in candidates if p.name.lower().startswith("scorecard")]
    feedback_files = [
        p for p in candidates
        if not p.name.lower().startswith("scorecard")
        and p.suffix.lower() in {".txt", ".md"}
    ]
    if len(scorecard_files) > 1:
        names = ", ".join(p.name for p in scorecard_files)
        sys.exit(
            f"error: multiple scorecard files detected ({names}). "
            "consolidate into a single scorecard file and rerun."
        )
    if not feedback_files:
        sys.exit("error: no partner feedback .txt or .md files in inputs/. drop 3-5 feedback artifacts there and rerun.")
    parts = [f"### {p.name}\n{p.read_text(encoding='utf-8').strip()}" for p in feedback_files]
    partner_msg = "\n\n".join(parts)
    scorecard_content = scorecard_files[0].read_text(encoding="utf-8").strip() if scorecard_files else None
    return partner_msg, scorecard_content, feedback_files + scorecard_files


def build_tool_definition() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return {
        "name": TOOL_NAME,
        "description": "Return a structured M6 design-partner-feedback synthesis matching the provided schema. Always call this tool.",
        "input_schema": schema,
    }


def call_claude(client: Anthropic, system: str, user_msg: str, tool: dict) -> dict:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                tools=[tool],
                tool_choice={"type": "tool", "name": TOOL_NAME},
            )
            for block in resp.content:
                if block.type == "tool_use" and block.name == TOOL_NAME:
                    return block.input
            raise RuntimeError("Claude returned no tool_use block for synthesize_feedback.")
        except APIError as exc:
            last_error = exc
            if attempt == 0:
                print(f"warning: API error, retrying once... ({exc})", file=sys.stderr)
    sys.exit(f"error: Claude call failed twice: {last_error}")


def format_slack_markdown(s: dict) -> str:
    lines: list[str] = [
        f"*M6 Design Partner Synthesis — {s['fellow_id']}*",
        f"_{s['synthesis_date']} · {s['design_partners_synthesized']} partners synthesized_",
        "",
        f"*Gate G4 Readiness:* {s['g4_readiness_score']}/10",
        f"> {s['g4_readiness_rationale']}",
        "",
        "*Top Themes*",
    ]
    for i, t in enumerate(s["themes"], 1):
        lines.append(f"{i}. *{t['theme']}* _({t['severity']})_ — {t['summary']}")
        lines.append(f"   Raised by: {', '.join(t['partners_raising'])}")
    lines += ["", "*Critical Objections*"]
    lines += [f"- {o['objection']} — _{o['partner_source']}_{' 🛑' if o['blocks_paying'] else ''}"
              for o in s["critical_objections"]] or ["None raised."]
    lines += ["", "*Must-fix for Gate G4*"]
    lines += [f"- {item}" for item in s["must_fix_for_g4"]]
    lines += ["", "*Nice-to-have (post-launch)*"]
    lines += [f"- {item}" for item in s["nice_to_have_post_launch"]] or ["None flagged."]
    lines += ["", "*Kill Signal Flags*"]
    if not s["kill_signal_flags"]:
        lines.append("None triggered.")
    for f in s["kill_signal_flags"]:
        lines.append(f"- ⚠️ *{f['signal']}* — {f['rationale']}")
        lines.append(f"  _Triggered by:_ \"{f['triggered_by']}\"")
    lines += ["", "*Scorecard*"]
    if s["scorecard_present"]:
        lines.append("Scorecard ingested.")
    else:
        lines.append("⚠️ No scorecard provided — readiness score reflects qualitative evidence only.")
    if s["scorecard_gaps_flagged"]:
        lines += ["", "_Metrics that should be tracked:_"]
        lines += [f"- {gap}" for gap in s["scorecard_gaps_flagged"]]
    lines += ["", "*Next Sprint Brief*", s["next_sprint_brief"]]
    return "\n".join(lines)


def clear_prior_outputs() -> None:
    # Keep outputs/ empty at the start of each run so the user can tell new from old.
    # If a same-named twin exists in the latest archive folder, drop the leftover; else move it there.
    leftovers = [p for p in OUTPUTS_DIR.iterdir() if p.is_file() and p.name != ".gitkeep"]
    if not leftovers:
        return
    archives = sorted(p for p in ARCHIVE_DIR.iterdir() if p.is_dir())
    if not archives:
        return
    latest = archives[-1]
    for p in leftovers:
        twin = latest / p.name
        p.unlink() if twin.exists() else shutil.move(str(p), twin)


def archive_run(input_files: list[Path], output_files: list[Path]) -> Path:
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    dest = ARCHIVE_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for p in input_files:
        shutil.move(str(p), dest / p.name)
    for p in output_files:
        shutil.copy2(str(p), dest / p.name)
    return dest


def main() -> None:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("error: ANTHROPIC_API_KEY is not set. copy .env.example to .env and paste your key.")
    client = Anthropic()

    partner_msg, scorecard_content, input_files = load_inputs()
    user_msg = partner_msg
    if scorecard_content is not None:
        user_msg = f"{partner_msg}\n\n### SCORECARD ARTIFACT\n{scorecard_content}"
    clear_prior_outputs()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    tool = build_tool_definition()
    synthesis = call_claude(client, system_prompt, user_msg, tool)

    OUTPUTS_DIR.mkdir(exist_ok=True)
    json_path = OUTPUTS_DIR / "synthesis.json"
    md_path = OUTPUTS_DIR / "synthesis.md"
    json_path.write_text(json.dumps(synthesis, indent=2, ensure_ascii=False), encoding="utf-8")
    md_text = format_slack_markdown(synthesis)
    md_path.write_text(md_text, encoding="utf-8")

    print(md_text)
    print()

    output_files: list[Path] = [json_path, md_path]
    route_error: str | None = None
    try:
        handoff_path = route.main(json_path)
        output_files.append(handoff_path)
    except SystemExit as exc:
        route_error = str(exc) or "route.py exited without details"
    except Exception as exc:
        route_error = f"{type(exc).__name__}: {exc}"

    archive_path = archive_run(input_files, output_files)
    print(f"\n[archived to {archive_path.relative_to(ROOT)}/]")
    if route_error:
        print(f"Synthesis completed and archived; routing failed: {route_error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
