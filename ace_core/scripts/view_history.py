#!/usr/bin/env python3
"""
Claude ACE - View Playbook History
Displays the evolution of the Playbook through Delta updates
"""
import sys
import json
from pathlib import Path
from datetime import datetime


def get_ace_dir() -> Path:
    """Get .claude directory"""
    project_dir = Path.cwd()
    return project_dir / ".claude"


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_timestamp


def print_operation(op: dict, indent: str = "    "):
    """Print a single operation with formatting"""
    op_type = op.get("type", "unknown")
    target = op.get("target", "")

    if op_type == "add":
        text = op.get("data", {}).get("text", "")
        reason = op.get("reason", "")
        print(f"{indent}✅ ADD: {target}")
        print(f"{indent}   Text: {text[:80]}{'...' if len(text) > 80 else ''}")
        if reason:
            print(f"{indent}   Reason: {reason}")

    elif op_type == "archive":
        reason = op.get("reason", "")
        print(f"{indent}📦 ARCHIVE: {target}")
        if reason:
            print(f"{indent}   Reason: {reason}")

    elif op_type == "score_update":
        delta = op.get("delta", 0)
        rating = op.get("rating", "")
        justification = op.get("justification", "")
        symbol = "📈" if delta > 0 else "📉"
        print(f"{indent}{symbol} SCORE UPDATE: {target}")
        print(f"{indent}   Delta: {delta:+d} ({rating})")
        if justification:
            print(f"{indent}   Justification: {justification[:80]}{'...' if len(justification) > 80 else ''}")


def view_history(limit: int = 20, source_filter: str = None, verbose: bool = False):
    """
    Display Playbook evolution history.

    Args:
        limit: Number of recent deltas to show
        source_filter: Only show deltas from specific source
        verbose: Show full details
    """
    ace_dir = get_ace_dir()
    history_file = ace_dir / "playbook_history.jsonl"

    if not history_file.exists():
        print("❌ No history file found")
        print(f"   Expected at: {history_file}")
        return

    # Read history
    deltas = []
    with open(history_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                deltas.append(json.loads(line))

    if not deltas:
        print("📭 No history entries found")
        return

    # Filter by source if requested
    if source_filter:
        deltas = [d for d in deltas if d.get("source") == source_filter]
        if not deltas:
            print(f"❌ No entries found for source: {source_filter}")
            return

    # Show most recent
    recent_deltas = deltas[-limit:]

    print("=" * 80)
    print(f"📜 PLAYBOOK EVOLUTION HISTORY")
    print(f"   Showing {len(recent_deltas)} most recent updates (total: {len(deltas)})")
    print("=" * 80)
    print()

    for i, delta in enumerate(reversed(recent_deltas), 1):
        timestamp = delta.get("timestamp", "")
        source = delta.get("source", "unknown")
        operations = delta.get("operations", [])
        playbook_size = delta.get("playbook_size", 0)
        avg_score = delta.get("avg_score", 0.0)

        print(f"[{i}] {format_timestamp(timestamp)}")
        print(f"    Source: {source}")
        print(f"    Operations: {len(operations)}")
        print(f"    Playbook Size: {playbook_size} key points")
        print(f"    Avg Score: {avg_score:.2f}")

        if verbose or len(operations) <= 5:
            print(f"    Details:")
            for op in operations:
                print_operation(op)
        elif operations:
            # Show summary
            op_types = {}
            for op in operations:
                op_type = op.get("type", "unknown")
                op_types[op_type] = op_types.get(op_type, 0) + 1

            print(f"    Summary:", end="")
            for op_type, count in op_types.items():
                print(f" {op_type}={count}", end="")
            print()

        print()


def view_stats():
    """Display statistics about Playbook evolution"""
    ace_dir = get_ace_dir()
    history_file = ace_dir / "playbook_history.jsonl"

    if not history_file.exists():
        print("❌ No history file found")
        return

    stats = {
        "total_updates": 0,
        "total_additions": 0,
        "total_archival": 0,
        "total_score_updates": 0,
        "updates_by_source": {},
        "playbook_sizes": []
    }

    with open(history_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            delta = json.loads(line)
            stats["total_updates"] += 1
            stats["playbook_sizes"].append(delta.get("playbook_size", 0))

            source = delta.get("source", "unknown")
            stats["updates_by_source"][source] = stats["updates_by_source"].get(source, 0) + 1

            for op in delta.get("operations", []):
                op_type = op.get("type", "")
                if op_type == "add":
                    stats["total_additions"] += 1
                elif op_type == "archive":
                    stats["total_archival"] += 1
                elif op_type == "score_update":
                    stats["total_score_updates"] += 1

    print("=" * 80)
    print("📊 PLAYBOOK EVOLUTION STATISTICS")
    print("=" * 80)
    print()

    print(f"Total Updates: {stats['total_updates']}")
    print(f"Total Additions: {stats['total_additions']}")
    print(f"Total Archival: {stats['total_archival']}")
    print(f"Total Score Updates: {stats['total_score_updates']}")
    print()

    print("Updates by Source:")
    for source, count in sorted(stats["updates_by_source"].items(), key=lambda x: x[1], reverse=True):
        print(f"  • {source}: {count}")
    print()

    if stats["playbook_sizes"]:
        current_size = stats["playbook_sizes"][-1]
        max_size = max(stats["playbook_sizes"])
        min_size = min(stats["playbook_sizes"])
        avg_size = sum(stats["playbook_sizes"]) / len(stats["playbook_sizes"])

        print("Playbook Size Evolution:")
        print(f"  • Current: {current_size} key points")
        print(f"  • Peak: {max_size} key points")
        print(f"  • Minimum: {min_size} key points")
        print(f"  • Average: {avg_size:.1f} key points")
    print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="View Claude ACE Playbook evolution history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View recent history
  python view_history.py

  # View more entries
  python view_history.py --limit 50

  # Show full details
  python view_history.py --verbose

  # Filter by source
  python view_history.py --source precompact

  # Show statistics
  python view_history.py --stats
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of recent updates to show (default: 20)'
    )

    parser.add_argument(
        '--source',
        type=str,
        help='Filter by source (e.g., precompact, session_end)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show full operation details'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics instead of history'
    )

    args = parser.parse_args()

    if args.stats:
        view_stats()
    else:
        view_history(
            limit=args.limit,
            source_filter=args.source,
            verbose=args.verbose
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
