#!/usr/bin/env python3
"""
Claude ACE - Session End Hook
Performs comprehensive reflection at the end of a session
"""
import json
import sys
import asyncio
from pathlib import Path
from common import (
    load_playbook, save_playbook, load_transcript,
    extract_keypoints, update_playbook_data, get_ace_dir
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


def process_tool_events(session_id: str) -> dict:
    """
    Process tool events collected during the session.

    Returns:
        Dict with error patterns and feedback for learning
    """
    events_dir = get_ace_dir() / "tool_events"

    if not events_dir.exists():
        return {'errors': [], 'patterns': []}

    # Collect events from this session
    session_events = []
    try:
        for event_file in events_dir.glob("event_*.json"):
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    event = json.load(f)
                    if event.get('session_id') == session_id:
                        session_events.append(event)
                        # Delete processed event
                        event_file.unlink()
            except Exception as e:
                print(f"Warning: Failed to process event file {event_file}: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"Warning: Failed to read tool events: {e}", file=sys.stderr)
        return {'errors': [], 'patterns': []}

    if not session_events:
        return {'errors': [], 'patterns': []}

    # Analyze error patterns
    error_summary = {
        'errors': [],
        'patterns': []
    }

    # Group by error category
    error_by_category = {}
    for event in session_events:
        category = event.get('error_category', 'unknown')
        if category not in error_by_category:
            error_by_category[category] = []
        error_by_category[category].append(event)

    # Create learning points from errors
    for category, events in error_by_category.items():
        if len(events) >= 2:
            # Repeated error - important pattern
            error_summary['patterns'].append({
                'category': category,
                'count': len(events),
                'severity': events[0].get('error_severity', 'medium'),
                'sample_error': events[0].get('stderr', '')[:200]
            })
        else:
            # Single error
            error_summary['errors'].append({
                'category': category,
                'tool': events[0].get('tool_name'),
                'command': events[0].get('command', '')[:100],
                'stderr': events[0].get('stderr', '')[:200]
            })

    print(f"Processed {len(session_events)} tool events: {len(error_summary['errors'])} errors, "
          f"{len(error_summary['patterns'])} patterns", file=sys.stderr)

    return error_summary


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

        # Process tool events from this session
        session_id = input_data.get("session_id", "unknown")
        tool_feedback = process_tool_events(session_id)

        # Extract comprehensive learnings from entire session
        # Include tool errors as additional feedback
        extraction_result = await extract_keypoints(
            messages,
            playbook,
            "session_end_reflection",
            feedback=tool_feedback
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
