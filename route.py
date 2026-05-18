from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic, APIError
from dotenv import load_dotenv

MODEL = "claude-sonnet-4-6"
TEXT_MAX_TOKENS = 2048
TICKETS_MAX_TOKENS = 4096
TICKETS_TOOL_NAME = "draft_linear_tickets"

ROOT = Path(__file__).parent
OUTPUTS_DIR = ROOT / "outputs"
PROMPT_PATH = ROOT / "prompts" / "route_system_prompt.md"
TICKETS_SCHEMA_PATH = ROOT / "schemas" / "linear_tickets_schema.json"


def load_synthesis(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"error: {path.name} not found in {path.parent.name}/. Run python run.py first.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {path.name} is malformed JSON: {exc}")


def determine_route(synthesis: dict) -> str:
    has_kill = bool(synthesis.get("kill_signal_flags"))
    score = synthesis.get("g4_readiness_score", 0)
    if has_kill or score <= 3:
        return "escalate"
    if score <= 7:
        return "tickets"
    return "ready"


def _user_msg(mode_block: str, synthesis: dict) -> str:
    pretty = json.dumps(synthesis, indent=2, ensure_ascii=False)
    return f"### MODE: {mode_block}\n\n### SYNTHESIS INPUT\n{pretty}"


def _call_text(client: Anthropic, system: str, user_msg: str) -> str:
    last: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=TEXT_MAX_TOKENS, system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        except APIError as exc:
            last = exc
            if attempt == 0:
                print(f"warning: API error, retrying once... ({exc})", file=sys.stderr)
    sys.exit(f"error: Claude call failed twice: {last}")


def _call_tickets(client: Anthropic, system: str, user_msg: str, tool: dict) -> dict:
    last: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=TICKETS_MAX_TOKENS, system=system,
                messages=[{"role": "user", "content": user_msg}],
                tools=[tool], tool_choice={"type": "tool", "name": TICKETS_TOOL_NAME},
            )
            for block in resp.content:
                if block.type == "tool_use" and block.name == TICKETS_TOOL_NAME:
                    return block.input
            raise RuntimeError("Claude returned no tool_use block for draft_linear_tickets.")
        except APIError as exc:
            last = exc
            if attempt == 0:
                print(f"warning: API error, retrying once... ({exc})", file=sys.stderr)
    sys.exit(f"error: Claude call failed twice: {last}")


def generate_escalation(client: Anthropic, system: str, synthesis: dict) -> str:
    return _call_text(client, system, _user_msg(
        "ESCALATION\nGenerate a Slack-ready escalation draft for the studio-only channel.", synthesis))


def generate_ready_brief(client: Anthropic, system: str, synthesis: dict) -> str:
    return _call_text(client, system, _user_msg(
        "G4_READY_BRIEF\nGenerate the handoff brief for M7 Go-to-Market.", synthesis))


def generate_tickets(client: Anthropic, system: str, synthesis: dict) -> dict:
    schema = json.loads(TICKETS_SCHEMA_PATH.read_text(encoding="utf-8"))
    tool = {
        "name": TICKETS_TOOL_NAME,
        "description": "Return one Linear ticket per must_fix_for_g4 item, conforming to the schema. Always call this tool.",
        "input_schema": schema,
    }
    msg = _user_msg(
        "LINEAR_TICKETS\nGenerate one ticket per item in must_fix_for_g4. "
        f"Every ticket's labels MUST include 'm6', 'g4-readiness', and '{synthesis['fellow_id']}'. "
        "Source field must be 'M6 Design Partner Synthesis Agent'.",
        synthesis,
    )
    return _call_tickets(client, system, msg, tool)


def _summarize_tickets(payload: dict) -> str:
    return "\n".join(f"- [{t['priority']}] {t['title']}" for t in payload["tickets"])


def main(synthesis_path: Path) -> Path:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("error: ANTHROPIC_API_KEY is not set. copy .env.example to .env and paste your key.")
    client = Anthropic()
    synthesis = load_synthesis(synthesis_path)
    route = determine_route(synthesis)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    OUTPUTS_DIR.mkdir(exist_ok=True)
    score = synthesis["g4_readiness_score"]
    flags = synthesis["kill_signal_flags"]

    if route == "escalate":
        content = generate_escalation(client, system_prompt, synthesis)
        out_path = OUTPUTS_DIR / "escalation.md"
        out_path.write_text(content, encoding="utf-8")
        reason = ", ".join(f["signal"] for f in flags) if flags else "low score"
        print(f"Route: escalate · {len(flags)} kill signal(s) fired ({reason}), score {score}/10 → outputs/{out_path.name}")
        print()
        print(content)
    elif route == "tickets":
        payload = generate_tickets(client, system_prompt, synthesis)
        out_path = OUTPUTS_DIR / "linear_tickets.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Route: tickets · No kill signals, score {score}/10 → outputs/{out_path.name} ({len(payload['tickets'])} tickets)")
        print()
        print(_summarize_tickets(payload))
    else:
        content = generate_ready_brief(client, system_prompt, synthesis)
        out_path = OUTPUTS_DIR / "g4_ready_brief.md"
        out_path.write_text(content, encoding="utf-8")
        print(f"Route: ready · No kill signals, score {score}/10 → outputs/{out_path.name}")
        print()
        print(content)
    return out_path


if __name__ == "__main__":
    main(OUTPUTS_DIR / "synthesis.json")
