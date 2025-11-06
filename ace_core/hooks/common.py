#!/usr/bin/env python3
"""
Claude ACE - Common utilities for hooks
Shared functions for playbook management, reflection, and learning
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Check for Claude Agent SDK availability
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, TextBlock
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("Warning: claude_agent_sdk not available. Reflection features disabled.",
          file=sys.stderr)


def get_project_dir() -> Path:
    """
    Get the project root directory.
    Supports CLAUDE_PROJECT_DIR env variable for custom paths.
    """
    project_dir = os.getenv('CLAUDE_PROJECT_DIR')
    if project_dir:
        return Path(project_dir)
    # Default: 3 levels up from hooks/common.py
    return Path(__file__).resolve().parent.parent.parent


def get_ace_dir() -> Path:
    """Get the .claude directory where ACE stores its data"""
    return get_project_dir() / ".claude"


def load_config() -> Dict[str, Any]:
    """Load ACE configuration with defaults"""
    config_path = get_ace_dir() / "ace_config.json"

    # Default configuration
    default_config = {
        "reflection": {
            "min_atomicity_score": 0.70,
            "max_keypoints_to_inject": 15,
            "auto_cleanup_threshold": -5
        },
        "scoring": {
            "helpful_delta": 1,
            "neutral_delta": -1,
            "harmful_delta": -3
        },
        "hooks": {
            "enable_user_prompt_inject": True,
            "enable_precompact": True,
            "enable_session_end": True,
            "inject_only_positive_scores": True
        }
    }

    if not config_path.exists():
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            # Merge with defaults
            return {**default_config, **user_config}
    except Exception as e:
        print(f"Warning: Failed to load config: {e}", file=sys.stderr)
        return default_config


def generate_keypoint_name(existing_names: set) -> str:
    """
    Generate unique key point name in format: kpt_001, kpt_002, etc.

    Args:
        existing_names: Set of already used keypoint names

    Returns:
        New unique keypoint name
    """
    max_num = 0
    for name in existing_names:
        if name.startswith("kpt_"):
            try:
                num = int(name.split("_")[1])
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue

    return f"kpt_{max_num + 1:03d}"


def load_playbook() -> Dict[str, Any]:
    """
    Load playbook with automatic migration and validation.
    Creates new playbook if none exists.

    Returns:
        Playbook dictionary with version, last_updated, and key_points
    """
    playbook_path = get_ace_dir() / "playbook.json"

    if not playbook_path.exists():
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": []
        }

    try:
        with open(playbook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure required fields
        if "key_points" not in data:
            data["key_points"] = []
        if "version" not in data:
            data["version"] = "1.0"

        # Migrate old format: ensure all key points have name, score, and status
        keypoints = []
        existing_names = set()

        for item in data["key_points"]:
            if isinstance(item, str):
                # Old format: plain string
                name = generate_keypoint_name(existing_names)
                keypoints.append({
                    "name": name,
                    "text": item,
                    "score": 0,
                    "status": "active"  # Default to active for old entries
                })
                existing_names.add(name)
            elif isinstance(item, dict):
                # New format: ensure all fields
                if "name" not in item:
                    item["name"] = generate_keypoint_name(existing_names)
                if "score" not in item:
                    item["score"] = 0
                if "status" not in item:
                    # Default to active for backward compatibility
                    item["status"] = "active"
                if "text" not in item:
                    continue  # Skip invalid entries
                existing_names.add(item["name"])
                keypoints.append(item)

        data["key_points"] = keypoints
        return data

    except Exception as e:
        print(f"Error loading playbook: {e}", file=sys.stderr)
        return {
            "version": "1.0",
            "last_updated": None,
            "key_points": []
        }


def save_playbook(playbook: Dict[str, Any]):
    """
    Save playbook to disk with timestamp update.

    Args:
        playbook: Playbook dictionary to save
    """
    playbook["last_updated"] = datetime.now().isoformat()
    playbook_path = get_ace_dir() / "playbook.json"

    # Ensure directory exists
    playbook_path.parent.mkdir(parents=True, exist_ok=True)

    with open(playbook_path, 'w', encoding='utf-8') as f:
        json.dump(playbook, f, indent=2, ensure_ascii=False)


def update_playbook_data(playbook: Dict[str, Any],
                         extraction_result: Dict[str, Any],
                         source: str = "unknown") -> Dict[str, Any]:
    """
    Update playbook with new key points and score adjustments using Delta mechanism.
    Implements incremental updates to prevent context collapse.

    Args:
        playbook: Current playbook
        extraction_result: Result from extract_keypoints with new_key_points and evaluations
        source: Source of the update (e.g., "precompact", "session_end")

    Returns:
        Updated playbook
    """
    from delta_manager import PlaybookDelta, apply_delta, PlaybookHistory

    config = load_config()
    scoring = config["scoring"]

    new_key_points = extraction_result.get("new_key_points", [])
    evaluations = extraction_result.get("evaluations", [])

    # Create delta for this update
    delta = PlaybookDelta(source=source)

    existing_names = {kp["name"] for kp in playbook["key_points"]}
    existing_texts = {
        kp["text"].lower().strip(): kp["name"]
        for kp in playbook["key_points"]
        if kp.get("status") != "archived"  # Only check active points
    }

    # Add new key points to delta
    for item in new_key_points:
        # Support both string and dict format
        if isinstance(item, str):
            text = item
            atomicity_score = None
            evidence = ""
        elif isinstance(item, dict):
            text = item.get("text", "")
            atomicity_score = item.get("atomicity_score")
            evidence = item.get("evidence", "")
        else:
            continue

        if not text:
            continue

        # Check for duplicates (case-insensitive)
        text_lower = text.lower().strip()
        if text_lower in existing_texts:
            continue

        name = generate_keypoint_name(existing_names)
        new_kp = {
            "name": name,
            "text": text,
            "score": 0
        }

        # Store atomicity score if provided
        if atomicity_score is not None:
            new_kp["atomicity_score"] = atomicity_score

        # Store evidence if provided
        if evidence:
            new_kp["evidence"] = evidence

        # Add to delta instead of directly to playbook
        delta.add_keypoint(new_kp, reason=f"Extracted from {source}")
        existing_names.add(name)
        existing_texts[text_lower] = name

    # Update scores based on evaluations using delta
    rating_delta = {
        "helpful": scoring["helpful_delta"],
        "harmful": scoring["harmful_delta"],
        "neutral": scoring["neutral_delta"]
    }

    for eval_item in evaluations:
        name = eval_item.get("name", "")
        rating = eval_item.get("rating", "neutral")
        justification = eval_item.get("justification", "")

        if name in existing_names:
            score_delta = rating_delta.get(rating, 0)
            delta.update_score(name, score_delta, rating, justification)

    # Check for low-scoring key points to archive BEFORE applying delta
    # This ensures archival operations are included in the main delta
    threshold = config["reflection"]["auto_cleanup_threshold"]
    for kp in playbook["key_points"]:
        # Treat missing status as active (backward compatibility)
        # Only skip if explicitly marked as archived
        if kp.get("status") != "archived" and kp.get("score", 0) <= threshold:
            # Add archival to main delta (not separate delta)
            delta.remove_keypoint(
                kp["name"],
                reason=f"Score {kp.get('score', 0)} below threshold {threshold}"
            )

    # Apply complete delta to playbook (includes additions, updates, and archival)
    playbook = apply_delta(playbook, delta)

    # Record complete delta history (now includes archival operations)
    history = PlaybookHistory(get_ace_dir())
    history.record_delta(delta, playbook)

    return playbook


def load_transcript(transcript_path: str) -> List[Dict[str, str]]:
    """
    Extract user and assistant messages from Claude Code transcript.
    Filters out meta-messages and command outputs.

    Args:
        transcript_path: Path to transcript JSONL file

    Returns:
        List of conversation messages with role and content
    """
    conversations = []

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Filter message types
                if entry.get('type') not in ['user', 'assistant']:
                    continue
                if entry.get('isMeta') or entry.get('isVisibleInTranscriptOnly'):
                    continue

                message = entry.get('message', {})
                role = message.get('role')
                content = message.get('content', '')

                if not role or not content:
                    continue

                # Filter out command outputs
                if isinstance(content, str):
                    if '<command-name>' in content or '<local-command-stdout>' in content:
                        continue

                # Handle structured content (list of blocks)
                if isinstance(content, list):
                    text_parts = [
                        item.get('text', '')
                        for item in content
                        if isinstance(item, dict) and item.get('type') == 'text'
                    ]
                    if text_parts:
                        conversations.append({
                            'role': role,
                            'content': '\n'.join(text_parts)
                        })
                else:
                    conversations.append({
                        'role': role,
                        'content': content
                    })

    except Exception as e:
        print(f"Error loading transcript: {e}", file=sys.stderr)

    return conversations


async def extract_keypoints(messages: List[Dict[str, str]],
                           playbook: Dict[str, Any],
                           diagnostic_name: str = "reflection",
                           feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract key points using separated Reflector and Curator roles.
    Implements the ACE framework's role-based architecture.

    Args:
        messages: Conversation history
        playbook: Current playbook
        diagnostic_name: Name for diagnostic output file
        feedback: Optional external feedback from environment

    Returns:
        Dictionary with new_key_points, evaluations, and curation details
    """
    if not SDK_AVAILABLE:
        print("Warning: Claude Agent SDK not available, skipping extraction",
              file=sys.stderr)
        return {"new_key_points": [], "evaluations": []}

    # Import roles (they are installed in the same directory for easy import)
    try:
        from reflector import Reflector
        from curator import Curator
    except ImportError as e:
        print(f"Error: Reflector and Curator modules not found: {e}", file=sys.stderr)
        print("Please reinstall ACE with: python install.py --force", file=sys.stderr)
        return {"new_key_points": [], "evaluations": []}

    # Get templates directory
    templates_dir = get_ace_dir().parent / "ace_core" / "prompts"
    if not templates_dir.exists():
        # Fallback to current .claude/prompts
        templates_dir = get_ace_dir() / "prompts"

    # Step 1: Reflector analyzes what happened
    reflector = Reflector(templates_dir)
    reflection_result = await reflector.analyze(messages, playbook, feedback)

    # Step 2: Curator converts observations into actionable strategies
    config = load_config()
    curator = Curator(config)
    curated_result = curator.curate(reflection_result, playbook)

    # Diagnostic output if enabled
    if is_diagnostic_mode():
        diagnostic_data = {
            "reflection_raw": reflection_result.get("raw_reflection", ""),
            "observations_count": len(reflection_result.get("observations", [])),
            "patterns_count": len(reflection_result.get("patterns", [])),
            "evaluations_count": len(reflection_result.get("evaluations", [])),
            "curated_accepted": len(curated_result.get("new_key_points", [])),
            "curated_rejected": len(curated_result.get("rejected", [])),
            "curation_summary": curator.create_learning_summary(curated_result)
        }
        save_diagnostic(json.dumps(diagnostic_data, indent=2, ensure_ascii=False), diagnostic_name)

    # Return curated result (compatible with existing code)
    return {
        "new_key_points": curated_result.get("new_key_points", []),
        "evaluations": curated_result.get("evaluations", []),
        "rejected": curated_result.get("rejected", []),
        "curation_summary": curated_result.get("curation_summary", {}),
        "reflection_result": reflection_result  # Keep for debugging
    }


def load_template(template_name: str) -> str:
    """
    Load prompt template from ace_core/prompts or .claude/prompts.

    Args:
        template_name: Name of template file

    Returns:
        Template content as string
    """
    # Try project-specific template first
    project_template = get_ace_dir() / "prompts" / template_name
    if project_template.exists():
        with open(project_template, 'r', encoding='utf-8') as f:
            return f.read()

    # Fall back to default template
    default_template = Path(__file__).parent.parent / "prompts" / template_name
    if default_template.exists():
        with open(default_template, 'r', encoding='utf-8') as f:
            return f.read()

    raise FileNotFoundError(f"Template not found: {template_name}")


def is_diagnostic_mode() -> bool:
    """Check if diagnostic mode is enabled"""
    flag_file = get_ace_dir() / "diagnostic_mode"
    return flag_file.exists()


def save_diagnostic(content: str, name: str):
    """
    Save diagnostic output with timestamp.

    Args:
        content: Content to save
        name: Base name for file (timestamp will be prepended)
    """
    diagnostic_dir = get_ace_dir() / "diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = diagnostic_dir / f"{timestamp}_{name}.txt"

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Diagnostic saved: {filepath}", file=sys.stderr)
