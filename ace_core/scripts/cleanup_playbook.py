#!/usr/bin/env python3
"""
Claude ACE - Playbook Cleanup Tool
Remove duplicates and low-scoring entries from the playbook
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher


def get_playbook_path():
    """Get path to playbook.json"""
    current = Path.cwd()

    if (current / ".claude" / "playbook.json").exists():
        return current / ".claude" / "playbook.json"

    if (current.parent / ".claude" / "playbook.json").exists():
        return current.parent / ".claude" / "playbook.json"

    if len(sys.argv) > 1 and '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            explicit_path = Path(sys.argv[idx + 1])
            if explicit_path.exists():
                return explicit_path

    return None


def similarity(text1, text2):
    """Calculate similarity ratio between two texts"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def cleanup_playbook(dry_run=True, threshold=-5, similarity_threshold=0.85):
    """
    Clean up playbook by removing:
    1. Low-scoring entries (below threshold)
    2. Duplicate entries (similar text)

    Args:
        dry_run: If True, only show what would be removed
        threshold: Score threshold for removal
        similarity_threshold: Text similarity threshold for duplicates
    """
    playbook_path = get_playbook_path()

    if not playbook_path:
        print("❌ No playbook found!")
        print("\nUsage:")
        print("  python cleanup_playbook.py [options]")
        print("\nOptions:")
        print("  --apply              Apply changes (default is dry-run)")
        print("  --threshold N        Set score threshold (default: -5)")
        print("  --similarity N       Set similarity threshold 0-1 (default: 0.85)")
        print("  --file PATH          Specify playbook file path")
        sys.exit(1)

    with open(playbook_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data.get('key_points', []))
    key_points = data.get('key_points', [])

    print("═" * 80)
    print("🧹 CLAUDE ACE PLAYBOOK CLEANUP")
    print("═" * 80)
    print(f"File: {playbook_path}")
    print(f"Original: {original_count} key points")
    print(f"Score Threshold: {threshold}")
    print(f"Similarity Threshold: {similarity_threshold:.0%}")
    print("─" * 80)

    # Step 1: Remove low scores
    removed_low = []
    kept_points = []

    for kp in key_points:
        if kp.get('score', 0) <= threshold:
            removed_low.append(kp)
        else:
            kept_points.append(kp)

    print(f"\n📉 Low Score Removal (≤{threshold}):")
    if removed_low:
        for kp in removed_low:
            print(f"   ❌ [{kp['name']}] Score: {kp.get('score', 0):+d}")
            print(f"      {kp['text'][:70]}...")
    else:
        print("   ✓ No low-scoring entries found")

    # Step 2: Remove duplicates
    removed_dup = []
    unique_points = []
    seen_texts = []

    for kp in kept_points:
        text = kp['text']
        is_duplicate = False

        for seen_text in seen_texts:
            if similarity(text, seen_text) >= similarity_threshold:
                is_duplicate = True
                removed_dup.append(kp)
                break

        if not is_duplicate:
            unique_points.append(kp)
            seen_texts.append(text)

    print(f"\n🔄 Duplicate Removal (≥{similarity_threshold:.0%} similar):")
    if removed_dup:
        for kp in removed_dup:
            print(f"   ❌ [{kp['name']}] Score: {kp.get('score', 0):+d}")
            print(f"      {kp['text'][:70]}...")
    else:
        print("   ✓ No duplicates found")

    # Summary
    final_count = len(unique_points)
    total_removed = original_count - final_count

    print("\n" + "─" * 80)
    print("📊 Summary:")
    print(f"   Original:         {original_count}")
    print(f"   Removed (low):    {len(removed_low)}")
    print(f"   Removed (dup):    {len(removed_dup)}")
    print(f"   Final:            {final_count}")
    print(f"   Total Removed:    {total_removed}")
    print(f"   Reduction:        {total_removed/original_count*100:.1f}%" if original_count > 0 else "")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes saved")
        print("   Run with --apply to save changes")
    else:
        # Save cleaned playbook
        data['key_points'] = unique_points
        data['last_updated'] = datetime.now().isoformat()

        # Backup original
        backup_path = playbook_path.parent / f"playbook.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Save cleaned version
        with open(playbook_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Changes saved!")
        print(f"   Backup: {backup_path}")
        print(f"   Updated: {playbook_path}")

    print("═" * 80)


if __name__ == "__main__":
    try:
        # Parse arguments
        dry_run = '--apply' not in sys.argv

        threshold = -5
        if '--threshold' in sys.argv:
            idx = sys.argv.index('--threshold')
            if idx + 1 < len(sys.argv):
                threshold = int(sys.argv[idx + 1])

        similarity_threshold = 0.85
        if '--similarity' in sys.argv:
            idx = sys.argv.index('--similarity')
            if idx + 1 < len(sys.argv):
                similarity_threshold = float(sys.argv[idx + 1])

        cleanup_playbook(dry_run, threshold, similarity_threshold)

    except KeyboardInterrupt:
        print("\n\nCleanup interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
