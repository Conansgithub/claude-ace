#!/usr/bin/env python3
"""
Claude ACE - PreCompact Hook
Extracts key points before context compaction occurs
"""
import json
import sys
import asyncio
from common import (
    load_playbook, save_playbook, load_transcript,
    extract_keypoints, update_playbook_data
)

# Try to import vector store for index updates
try:
    from storage.vector_store import PlaybookVectorStore
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False


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

        # Extract new learnings and evaluate existing ones
        extraction_result = await extract_keypoints(
            messages,
            playbook,
            "precompact_reflection"
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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("PreCompact hook interrupted", file=sys.stderr)
        sys.exit(1)
