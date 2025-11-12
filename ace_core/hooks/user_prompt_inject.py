#!/usr/bin/env python3
"""
Claude ACE - User Prompt Inject Hook
Injects playbook knowledge at the start of new sessions

Enhanced with vector search for semantic relevance
"""
import json
import sys
from pathlib import Path
from common import (
    load_playbook, load_template, is_diagnostic_mode,
    save_diagnostic, get_ace_dir, load_config
)

# Try to import vector store
try:
    from storage.vector_store import PlaybookVectorStore
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    print("Note: Vector search not available, using fallback method", file=sys.stderr)


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


def format_playbook_with_vector_search(playbook: dict, user_query: str) -> str:
    """
    Format playbook using vector search for relevance.

    Args:
        playbook: Playbook dictionary
        user_query: User's message to find relevant strategies

    Returns:
        Formatted string for injection
    """
    config = load_config()
    max_points = config["reflection"]["max_keypoints_to_inject"]

    try:
        # Initialize vector store
        vector_store = PlaybookVectorStore()

        # Check if index exists, if not create it
        if not vector_store.is_indexed():
            print("Indexing playbook for first time...", file=sys.stderr)
            indexed_count = vector_store.index_playbook(playbook)
            print(f"Indexed {indexed_count} strategies", file=sys.stderr)

        # Search for relevant strategies
        # Only search positive-score strategies
        results = vector_store.search(
            query=user_query,
            limit=max_points,
            min_score=0  # Only positive scores
        )

        if not results:
            return ""

        # Format with similarity indicators
        key_points_text = "\n".join(
            f"- [{r['name']}] {r['text']} (relevance: {r['similarity']:.0%})"
            for r in results
        )

        # Load and format template
        template = load_template("playbook.txt")
        return template.format(key_points=key_points_text)

    except Exception as e:
        print(f"Vector search failed: {e}, using fallback", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Fall back to simple method
        return format_playbook_simple(playbook)


def format_playbook_simple(playbook: dict) -> str:
    """
    Format playbook key points using simple score-based ranking.
    This is the fallback method when vector search is not available.

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

        # Load playbook
        playbook = load_playbook()

        # Try to get user message for vector search
        user_message = input_data.get('userMessage', '')

        # Format playbook with best available method
        if VECTOR_SEARCH_AVAILABLE and user_message:
            print("Using vector search for strategy selection", file=sys.stderr)
            context = format_playbook_with_vector_search(playbook, user_message)
        else:
            if not user_message:
                print("No user message available, using simple ranking", file=sys.stderr)
            context = format_playbook_simple(playbook)

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
