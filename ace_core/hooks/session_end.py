#!/usr/bin/env python3
"""
Claude ACE - Session End Hook
Performs comprehensive reflection at the end of a session
"""
import json
import sys
import asyncio
from common import (
    load_playbook, save_playbook, load_transcript,
    extract_keypoints, update_playbook_data
)


def _run_async_safe(coro):
    """Safely run async coroutine, handling existing event loops"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Event loop already running - shouldn't happen but handle it
        print("Warning: Running in existing event loop context", file=sys.stderr)
        return loop.run_until_complete(coro)


async def main():
    """Main entry point for session end hook"""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        transcript_path = input_data.get("transcript_path")
        if not transcript_path:
            print("Warning: No transcript_path provided", file=sys.stderr)
            sys.exit(0)

        # Load conversation messages
        messages = load_transcript(transcript_path)

        if not messages:
            print("No messages to process", file=sys.stderr)
            sys.exit(0)

        print(f"Session End: Processing {len(messages)} messages for final reflection",
              file=sys.stderr)

        # Load current playbook
        playbook = load_playbook()

        # Extract comprehensive learnings from entire session
        extraction_result = await extract_keypoints(
            messages,
            playbook,
            "session_end_reflection"
        )

        # Update playbook with results (using Delta mechanism)
        playbook = update_playbook_data(playbook, extraction_result, source="session_end")

        # Save updated playbook
        save_playbook(playbook)

        new_count = len(extraction_result.get("new_key_points", []))
        eval_count = len(extraction_result.get("evaluations", []))
        total_points = len(playbook.get("key_points", []))

        print(f"Session End: Added {new_count} new key points, "
              f"evaluated {eval_count} existing points. "
              f"Total playbook size: {total_points}",
              file=sys.stderr)

    except Exception as e:
        print(f"Error in session_end hook: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        _run_async_safe(main())
    except KeyboardInterrupt:
        print("Session End hook interrupted", file=sys.stderr)
        sys.exit(1)
