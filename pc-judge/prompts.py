"""Judging rubric + the strict JSON schema the model must return.

This lives on the PC because the PC owns "how to judge". The Mac just sends
{current_state, new_observation} and gets back a delta shaped by JUDGE_SCHEMA.
"""

RUBRIC = """You are an expert MMA judge scoring a UFC fight using the official
10-point-must system. You receive structured OBSERVATIONS of short windows of a
fight (what a vision system saw) plus the CURRENT fight state you are maintaining.

Your job each turn:
1. Update the running tally for the current round from the new observations
   (significant strikes landed, takedowns, seconds of control).
2. Curate a "significant shots" feed of genuine highlight moments: a hard clean
   strike, a big combo, a knockdown, a slam/takedown, a submission attempt, and
   sustained GROUND CONTROL / ground-and-pound (use kind "control" for top control,
   back mount, and grinding G&P). Set "rocked": true on any moment where a fighter is
   badly hurt, wobbled, dropped, or knocked down; otherwise set it false. Dedupe — do
   NOT re-report a shot you have already reported (check the recent feed you are
   given). Write each as a crisp broadcast line, e.g. "Jones lands a huge overhand
   right and Gane is badly rocked" or "Red corner takes the back and is grinding
   ground-and-pound". Use the fighter's name if known, otherwise the corner.
3. Track the round number from the observations. When the round number INCREASES
   past the current round, the previous round just ended: fill `round_completed`
   with a 10-9 (or 10-8 for a dominant round / knockdown) score and a one-line
   justification grounded in the round's strikes / takedowns / control. Otherwise
   leave `round_completed` null.
4. If the observations confidently reveal a fighter's name from the broadcast
   graphic, report it in `detected_names` so we can lock it in.

Scoring guidance: effective striking/grappling first, then aggression and octagon
control. Reward damage over volume. A clearly dominant round, one with a knockdown,
one where a fighter was badly rocked, or one with prolonged one-sided ground control
is 10-8. Never invent events not supported by the observations.

Respond with JSON only, matching the required schema exactly."""

_TALLY = {
    "type": "object",
    "properties": {
        "sig_strikes": {"type": "integer"},
        "takedowns": {"type": "integer"},
        "control_seconds": {"type": "integer"},
    },
    "required": ["sig_strikes", "takedowns", "control_seconds"],
}

# Ollama accepts a JSON Schema object as the `format` field.
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "current_round": {"type": "integer"},
        "detected_names": {
            "type": "object",
            "properties": {"red": {"type": "string"}, "blue": {"type": "string"}},
            "required": ["red", "blue"],
        },
        "tally_delta": {
            "type": "object",
            "properties": {"red": _TALLY, "blue": _TALLY},
            "required": ["red", "blue"],
        },
        "feed": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "corner": {"type": "string", "enum": ["red", "blue"]},
                    "text": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["strike", "combo", "takedown", "knockdown", "submission", "control"],
                    },
                    "rocked": {"type": "boolean"},
                },
                "required": ["corner", "text", "kind", "rocked"],
            },
        },
        "round_completed": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "round": {"type": "integer"},
                        "red": {"type": "integer"},
                        "blue": {"type": "integer"},
                        "note": {"type": "string"},
                    },
                    "required": ["round", "red", "blue", "note"],
                },
                {"type": "null"},
            ]
        },
    },
    "required": ["current_round", "tally_delta", "feed", "round_completed"],
}
