#!/usr/bin/env python3
"""
Claude ACE - User Prompt Inject Hook
Injects playbook knowledge at the start of new sessions
"""
import json
import sys
from pathlib import Path
from common import (
    load_playbook, load_template, is_diagnostic_mode,
    save_diagnostic, get_ace_dir, load_config
)


def is_first_message(session_id: str) -> bool:
    """
    Check if this is the first message of a new session.

    Args:
        session_id: Current session identifier

    Returns:
        True if this is a new session
    """
    session_file = get_ace_dir() / "last_session.txt"

    if session_file.exists():
        try:
            last_session_id = session_file.read_text().strip()
            return session_id != last_session_id
        except:
            return True

    return True


def mark_session(session_id: str):
    """
    Mark current session as seen.

    Args:
        session_id: Session identifier to record
    """
    session_file = get_ace_dir() / "last_session.txt"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)


def format_playbook(playbook: dict) -> str:
    """
    Format playbook key points for injection into user prompt.

    Args:
        playbook: Playbook dictionary

    Returns:
        Formatted string for injection, or empty string if no points
    """
    config = load_config()
    hooks_config = config["hooks"]

    key_points = playbook.get('key_points', [])
    if not key_points:
        return ""

    # Filter out archived key points (only inject active ones)
    key_points = [kp for kp in key_points if kp.get('status') != 'archived']

    # Filter by score if configured
    if hooks_config.get("inject_only_positive_scores", True):
        key_points = [kp for kp in key_points if kp.get('score', 0) >= 0]

    if not key_points:
        return ""

    # Sort by score (highest first)
    sorted_kps = sorted(key_points,
                       key=lambda x: x.get('score', 0),
                       reverse=True)

    # Limit number of injected points
    max_points = config["reflection"]["max_keypoints_to_inject"]
    top_kps = sorted_kps[:max_points]

    # Format key points with IDs for reference
    key_points_text = "\n".join(
        f"- [{kp['name']}] {kp['text']}"
        for kp in top_kps
    )

    # Load and format template
    template = load_template("playbook.txt")
    return template.format(key_points=key_points_text)


def main():
    """Main entry point for user prompt inject hook"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        session_id = input_data.get('session_id', 'unknown')

        # Check if this is a new session
        if not is_first_message(session_id):
            print(json.dumps({}), flush=True)
            sys.exit(0)

        # Load and format playbook
        playbook = load_playbook()
        context = format_playbook(playbook)

        # If no context to inject, return empty
        if not context:
            print(json.dumps({}), flush=True)
            sys.exit(0)

        # Save diagnostic if enabled
        if is_diagnostic_mode():
            save_diagnostic(context, "user_prompt_inject")

        # Prepare response with additional context
        response = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context
            }
        }

        # Output response
        sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(response, ensure_ascii=False), flush=True)

        # Mark this session as seen
        mark_session(session_id)

    except Exception as e:
        print(f"Error in user_prompt_inject: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Return empty response on error
        print(json.dumps({}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
