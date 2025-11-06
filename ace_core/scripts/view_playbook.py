#!/usr/bin/env python3
"""
Claude ACE - Playbook Viewer
Interactive tool to view and analyze the knowledge base
"""
import json
import sys
from pathlib import Path
from datetime import datetime


def get_playbook_path():
    """Get path to playbook.json"""
    # Check if we're in project root or need to go up
    current = Path.cwd()

    # Try current directory
    if (current / ".claude" / "playbook.json").exists():
        return current / ".claude" / "playbook.json"

    # Try one level up
    if (current.parent / ".claude" / "playbook.json").exists():
        return current.parent / ".claude" / "playbook.json"

    # Try explicit path argument
    if len(sys.argv) > 1:
        explicit_path = Path(sys.argv[1])
        if explicit_path.exists():
            return explicit_path

    return None


def format_timestamp(iso_string):
    """Format ISO timestamp to readable string"""
    if not iso_string:
        return "Never"
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_string


def view_playbook():
    """Display playbook contents in a nice format"""
    playbook_path = get_playbook_path()

    if not playbook_path:
        print("❌ No playbook found!")
        print("\nUsage:")
        print("  python view_playbook.py [path/to/playbook.json]")
        print("\nOr run from project directory containing .claude/playbook.json")
        sys.exit(1)

    with open(playbook_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Header
    print("═" * 80)
    print("📚 CLAUDE ACE PLAYBOOK VIEWER")
    print("═" * 80)
    print(f"File: {playbook_path}")
    print(f"Version: {data.get('version', 'unknown')}")
    print(f"Last Updated: {format_timestamp(data.get('last_updated'))}")
    print(f"Total Key Points: {len(data.get('key_points', []))}")
    print("═" * 80)

    key_points = data.get('key_points', [])

    if not key_points:
        print("\n📭 Playbook is empty. Start using Claude Code to build knowledge!")
        return

    # Sort by score (highest first)
    sorted_kps = sorted(key_points,
                       key=lambda x: x.get('score', 0),
                       reverse=True)

    # Statistics
    positive = sum(1 for kp in key_points if kp.get('score', 0) > 0)
    neutral = sum(1 for kp in key_points if kp.get('score', 0) == 0)
    negative = sum(1 for kp in key_points if kp.get('score', 0) < 0)

    print(f"\n📊 Statistics:")
    print(f"   🌟 Positive Score: {positive}")
    print(f"   ⚖️  Neutral Score: {neutral}")
    print(f"   ⚠️  Negative Score: {negative}")

    # Display key points
    print(f"\n📋 Key Points:\n")

    for kp in sorted_kps:
        score = kp.get('score', 0)

        # Choose emoji based on score
        if score >= 3:
            emoji = "🌟"
            color = "\033[92m"  # Green
        elif score >= 0:
            emoji = "✅"
            color = "\033[94m"  # Blue
        elif score >= -2:
            emoji = "⚠️"
            color = "\033[93m"  # Yellow
        else:
            emoji = "❌"
            color = "\033[91m"  # Red

        reset = "\033[0m"

        print(f"{color}{emoji} {kp['name']} (Score: {score:+d}){reset}")
        print(f"   {kp['text']}")

        # Show atomicity score if available
        if 'atomicity_score' in kp:
            print(f"   💎 Atomicity: {kp['atomicity_score']:.0%}")

        # Show recent evaluations if available
        if 'evaluations' in kp and kp['evaluations']:
            recent = kp['evaluations'][-3:]  # Last 3 evaluations
            eval_summary = ", ".join([e.get('rating', '?') for e in recent])
            print(f"   📈 Recent: {eval_summary}")

        print()

    # Legend
    print("─" * 80)
    print("Legend:")
    print("  🌟 Highly Useful (≥3)  |  ✅ Good (0-2)  |  ⚠️  Under Review (-1,-2)  |  ❌ Problematic (≤-3)")
    print("═" * 80)


if __name__ == "__main__":
    try:
        view_playbook()
    except KeyboardInterrupt:
        print("\n\nViewer interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
