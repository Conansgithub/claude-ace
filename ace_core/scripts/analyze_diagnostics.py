#!/usr/bin/env python3
"""
Claude ACE - Diagnostic Analyzer
Analyze diagnostic logs to understand learning patterns and system behavior
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


def get_diagnostic_dir():
    """Get path to diagnostic directory"""
    current = Path.cwd()

    if (current / ".claude" / "diagnostic").exists():
        return current / ".claude" / "diagnostic"

    if (current.parent / ".claude" / "diagnostic").exists():
        return current.parent / ".claude" / "diagnostic"

    if len(sys.argv) > 1:
        explicit_path = Path(sys.argv[1])
        if explicit_path.exists() and explicit_path.is_dir():
            return explicit_path

    return None


def parse_diagnostic_file(filepath):
    """Extract information from a diagnostic file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    info = {
        'filepath': filepath,
        'size': len(content),
        'has_prompt': '# PROMPT' in content,
        'has_response': '# RESPONSE' in content,
        'has_error': 'ERROR' in content or 'Error' in content,
    }

    # Try to extract new key points count
    if '"new_key_points"' in content:
        try:
            # Find the JSON response section
            response_start = content.find('# RESPONSE')
            if response_start != -1:
                json_text = content[response_start:]
                # Try to parse JSON
                if '```json' in json_text:
                    start = json_text.find('```json') + 7
                    end = json_text.find('```', start)
                    if end != -1:
                        json_str = json_text[start:end].strip()
                        data = json.loads(json_str)
                        info['new_key_points_count'] = len(data.get('new_key_points', []))
                        info['evaluations_count'] = len(data.get('evaluations', []))
        except:
            pass

    return info


def analyze_diagnostics():
    """Analyze all diagnostic files and show statistics"""
    diag_dir = get_diagnostic_dir()

    if not diag_dir:
        print("❌ No diagnostic directory found!")
        print("\nDiagnostic mode is not enabled or no diagnostics have been generated.")
        print("\nTo enable diagnostic mode:")
        print("  touch .claude/diagnostic_mode")
        print("\nUsage:")
        print("  python analyze_diagnostics.py [path/to/diagnostic/dir]")
        sys.exit(1)

    files = sorted(diag_dir.glob("*.txt"))

    if not files:
        print("❌ No diagnostic files found in:", diag_dir)
        print("\nDiagnostic mode may be enabled but no sessions have been recorded yet.")
        sys.exit(0)

    print("═" * 80)
    print("🔍 CLAUDE ACE DIAGNOSTIC ANALYSIS")
    print("═" * 80)
    print(f"Directory: {diag_dir}")
    print(f"Total Files: {len(files)}")
    print("─" * 80)

    # Analyze by type
    types = Counter()
    dates = defaultdict(int)
    errors = []
    learning_stats = {
        'total_new_points': 0,
        'total_evaluations': 0,
        'sessions_with_learning': 0
    }

    print("\n📊 Analyzing files...")

    for f in files:
        # Parse filename: YYYYMMDD_HHMMSS_type.txt
        parts = f.stem.split('_')
        if len(parts) >= 3:
            date_str = parts[0]
            hook_type = '_'.join(parts[2:])
        else:
            hook_type = f.stem

        types[hook_type] += 1

        # Track by date
        if len(date_str) == 8:
            dates[date_str] += 1

        # Parse file content
        info = parse_diagnostic_file(f)

        if info.get('has_error'):
            errors.append(f.name)

        if 'new_key_points_count' in info:
            count = info['new_key_points_count']
            learning_stats['total_new_points'] += count
            if count > 0:
                learning_stats['sessions_with_learning'] += 1

        if 'evaluations_count' in info:
            learning_stats['total_evaluations'] += info['evaluations_count']

    # Display results
    print("\n📋 By Hook Type:")
    for hook_type, count in types.most_common():
        print(f"   {hook_type:<30} {count:>3} files")

    print("\n📅 By Date:")
    sorted_dates = sorted(dates.items(), reverse=True)[:10]  # Last 10 dates
    for date_str, count in sorted_dates:
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            formatted = date_obj.strftime("%Y-%m-%d")
        except:
            formatted = date_str
        print(f"   {formatted}    {count:>3} files")

    print("\n🧠 Learning Statistics:")
    print(f"   Total New Key Points:    {learning_stats['total_new_points']}")
    print(f"   Total Evaluations:       {learning_stats['total_evaluations']}")
    print(f"   Sessions w/ Learning:    {learning_stats['sessions_with_learning']}")
    if learning_stats['sessions_with_learning'] > 0:
        avg = learning_stats['total_new_points'] / learning_stats['sessions_with_learning']
        print(f"   Avg Points per Session:  {avg:.1f}")

    if errors:
        print("\n⚠️  Files with Errors:")
        for error_file in errors[:5]:  # Show first 5
            print(f"   {error_file}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    print("\n📈 Recent Activity (last 5 sessions):")
    for f in files[-5:]:
        timestamp_str = f.stem[:15]
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted = timestamp_str

        hook_type = '_'.join(f.stem.split('_')[2:])
        size = f.stat().st_size

        print(f"   {formatted}  {hook_type:<25}  {size:>6} bytes")

    print("\n💡 Tips:")
    print("   • View specific diagnostic: cat .claude/diagnostic/<filename>")
    print("   • Disable diagnostic mode: rm .claude/diagnostic_mode")
    print("   • Clear old diagnostics: rm .claude/diagnostic/*.txt")

    print("═" * 80)


if __name__ == "__main__":
    try:
        analyze_diagnostics()
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
