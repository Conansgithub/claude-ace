#!/usr/bin/env python3
"""
Claude ACE - PreCompact Hook
Extracts key points before context compaction occurs
"""
import json
import sys
import asyncio
from pathlib import Path
from common import (
    load_playbook, save_playbook, load_transcript,
    extract_keypoints, update_playbook_data, get_ace_dir
)

# Try to import vector store for index updates
try:
    from storage.vector_store import PlaybookVectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False


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


def get_tool_feedback(session_id: str) -> dict:
    """
    Get tool feedback without deleting events (PreCompact doesn't delete,
    SessionEnd will delete them).

    Returns:
        Dict with error patterns and feedback
    """
    events_dir = get_ace_dir() / "tool_events"

    if not events_dir.exists():
        return {'errors': [], 'patterns': []}

    # Collect events from this session (don't delete)
    session_events = []
    try:
        for event_file in events_dir.glob("event_*.json"):
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    event = json.load(f)
                    if event.get('session_id') == session_id:
                        session_events.append(event)
            except Exception:
                continue
    except Exception:
        return {'errors': [], 'patterns': []}

    if not session_events:
        return {'errors': [], 'patterns': []}

    # Summarize recent errors
    return {
        'errors': [
            {
                'category': e.get('error_category'),
                'tool': e.get('tool_name'),
                'severity': e.get('error_severity')
            }
            for e in session_events[-5:]  # Last 5 errors
        ],
        'patterns': []
    }



async def main():
    """Main entry point for precompact hook"""
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

        print(f"Processing {len(messages)} messages for learning extraction",
              file=sys.stderr)

        # Load current playbook
        playbook = load_playbook()

        # Get tool feedback (without deleting events)
        session_id = input_data.get("session_id", "unknown")
        tool_feedback = get_tool_feedback(session_id)

        # Extract new learnings and evaluate existing ones
        extraction_result = await extract_keypoints(
            messages,
            playbook,
            "precompact_reflection",
            feedback=tool_feedback
        )

        # Update playbook with results (using Delta mechanism)
        playbook = update_playbook_data(playbook, extraction_result, source="precompact")

        # Save updated playbook
        save_playbook(playbook)

        # Update vector index if available
        if VECTOR_STORE_AVAILABLE:
            try:
                vector_store = PlaybookVectorStore()
                indexed_count = vector_store.index_playbook(playbook)
                print(f"✓ Vector index updated ({indexed_count} strategies)", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to update vector index: {e}", file=sys.stderr)

        new_count = len(extraction_result.get("new_key_points", []))
        eval_count = len(extraction_result.get("evaluations", []))
        print(f"PreCompact: Added {new_count} new key points, "
              f"evaluated {eval_count} existing points",
              file=sys.stderr)

    except Exception as e:
        print(f"Error in precompact hook: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        _run_async_safe(main())
    except KeyboardInterrupt:
        print("PreCompact hook interrupted", file=sys.stderr)
        sys.exit(1)
