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

        # Migrate old format: ensure all key points have name and score
        keypoints = []
        existing_names = set()

        for item in data["key_points"]:
            if isinstance(item, str):
                # Old format: plain string
                name = generate_keypoint_name(existing_names)
                keypoints.append({
                    "name": name,
                    "text": item,
                    "score": 0
                })
                existing_names.add(name)
            elif isinstance(item, dict):
                # New format: ensure all fields
                if "name" not in item:
                    item["name"] = generate_keypoint_name(existing_names)
                if "score" not in item:
                    item["score"] = 0
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
                         extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update playbook with new key points and score adjustments.

    Args:
        playbook: Current playbook
        extraction_result: Result from extract_keypoints with new_key_points and evaluations

    Returns:
        Updated playbook
    """
    config = load_config()
    scoring = config["scoring"]

    new_key_points = extraction_result.get("new_key_points", [])
    evaluations = extraction_result.get("evaluations", [])

    existing_names = {kp["name"] for kp in playbook["key_points"]}
    existing_texts = {kp["text"].lower().strip() for kp in playbook["key_points"]}

    # Add new key points
    for item in new_key_points:
        # Support both string and dict format
        if isinstance(item, str):
            text = item
            atomicity_score = None
        elif isinstance(item, dict):
            text = item.get("text", "")
            atomicity_score = item.get("atomicity_score")
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

        playbook["key_points"].append(new_kp)
        existing_names.add(name)
        existing_texts.add(text_lower)

    # Update scores based on evaluations
    rating_delta = {
        "helpful": scoring["helpful_delta"],
        "harmful": scoring["harmful_delta"],
        "neutral": scoring["neutral_delta"]
    }

    name_to_kp = {kp["name"]: kp for kp in playbook["key_points"]}

    for eval_item in evaluations:
        name = eval_item.get("name", "")
        rating = eval_item.get("rating", "neutral")

        if name in name_to_kp:
            delta = rating_delta.get(rating, 0)
            name_to_kp[name]["score"] += delta

            # Store evaluation history (optional)
            if "evaluations" not in name_to_kp[name]:
                name_to_kp[name]["evaluations"] = []
            name_to_kp[name]["evaluations"].append({
                "rating": rating,
                "timestamp": datetime.now().isoformat()
            })

    # Remove key points below threshold
    threshold = config["reflection"]["auto_cleanup_threshold"]
    playbook["key_points"] = [
        kp for kp in playbook["key_points"]
        if kp.get("score", 0) > threshold
    ]

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
                           diagnostic_name: str = "reflection") -> Dict[str, Any]:
    """
    Use Claude Agent SDK to extract key points and evaluate playbook.

    Args:
        messages: Conversation history
        playbook: Current playbook
        diagnostic_name: Name for diagnostic output file

    Returns:
        Dictionary with new_key_points and evaluations
    """
    if not SDK_AVAILABLE:
        print("Warning: Claude Agent SDK not available, skipping extraction",
              file=sys.stderr)
        return {"new_key_points": [], "evaluations": []}

    # Load reflection template
    template = load_template("reflection.txt")

    # Format current playbook for prompt
    playbook_dict = {
        kp["name"]: kp["text"]
        for kp in playbook.get("key_points", [])
    }

    # Create prompt
    prompt = template.format(
        trajectories=json.dumps(messages, indent=2, ensure_ascii=False),
        playbook=json.dumps(playbook_dict, indent=2, ensure_ascii=False)
    )

    # Configure SDK client
    options = ClaudeAgentOptions(
        max_turns=1,
        permission_mode="bypassPermissions",
        allowed_tools=[]
    )

    response_text = ""
    client = ClaudeSDKClient(options=options)

    try:
        await client.connect()
        await client.query(prompt)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
    except Exception as e:
        print(f"Error during SDK extraction: {e}", file=sys.stderr)
        return {"new_key_points": [], "evaluations": []}
    finally:
        try:
            await client.disconnect()
        except:
            pass

    # Save diagnostic output
    if is_diagnostic_mode():
        diagnostic_content = f"# PROMPT\n{prompt}\n\n{'=' * 80}\n\n# RESPONSE\n{response_text}\n"
        save_diagnostic(diagnostic_content, diagnostic_name)

    # Parse JSON response
    json_text = extract_json_from_response(response_text)

    try:
        result = json.loads(json_text)
        return {
            "new_key_points": result.get("new_key_points", []),
            "evaluations": result.get("evaluations", [])
        }
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        if is_diagnostic_mode():
            save_diagnostic(f"JSON PARSE ERROR:\n{e}\n\nRAW TEXT:\n{json_text}",
                          f"{diagnostic_name}_parse_error")
        return {"new_key_points": [], "evaluations": []}


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON from various response formats.
    Handles markdown code blocks and plain JSON.
    """
    # Try to find JSON in markdown code block
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end != -1:
            return response_text[start:end].strip()

    # Try generic code block
    if "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end != -1:
            return response_text[start:end].strip()

    # Assume plain JSON
    return response_text.strip()


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
