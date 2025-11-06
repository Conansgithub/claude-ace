#!/usr/bin/env python3
"""
Claude ACE - Reflector Role
Analyzes conversation trajectories to identify what worked and what didn't.
Corresponds to the Reflector component in the ACE framework.
"""
import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path


# Check for Claude Agent SDK
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, TextBlock
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


class Reflector:
    """
    Reflector analyzes execution outcomes and identifies patterns.

    In the ACE framework, the Reflector's job is to:
    1. Analyze what worked and what didn't
    2. Identify successful patterns
    3. Detect failure modes
    4. Evaluate existing playbook items
    """

    def __init__(self, templates_dir: Path):
        """
        Initialize Reflector.

        Args:
            templates_dir: Directory containing prompt templates
        """
        self.templates_dir = templates_dir
        self.reflection_template = self._load_template("reflection.txt")

    def _load_template(self, template_name: str) -> str:
        """Load a prompt template"""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    async def analyze(self,
                     messages: List[Dict[str, str]],
                     playbook: Dict[str, Any],
                     feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze conversation trajectories to extract insights.

        Args:
            messages: Conversation history (list of {role, content})
            playbook: Current playbook with existing key points
            feedback: Optional external feedback (for environment feedback system)

        Returns:
            Dictionary with:
            - observations: List of what happened (successes/failures)
            - patterns: Identified patterns in behavior
            - evaluations: Assessment of existing playbook items
            - raw_reflection: Full reflection text
        """
        if not SDK_AVAILABLE:
            print("Warning: Claude Agent SDK not available, reflection disabled",
                  file=sys.stderr)
            return {
                "observations": [],
                "patterns": [],
                "evaluations": [],
                "raw_reflection": ""
            }

        # Format playbook for prompt
        playbook_dict = {
            kp["name"]: kp["text"]
            for kp in playbook.get("key_points", [])
            if kp.get("status") != "archived"  # Only include active points
        }

        # Prepare trajectories with optional feedback
        trajectories_data = {
            "messages": messages,
            "message_count": len(messages)
        }

        if feedback:
            trajectories_data["external_feedback"] = feedback

        # Create reflection prompt
        prompt = self.reflection_template.format(
            trajectories=json.dumps(trajectories_data, indent=2, ensure_ascii=False),
            playbook=json.dumps(playbook_dict, indent=2, ensure_ascii=False)
        )

        # Use Claude SDK for reflection
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
            print(f"Error during reflection: {e}", file=sys.stderr)
            return {
                "observations": [],
                "patterns": [],
                "evaluations": [],
                "raw_reflection": "",
                "error": str(e)
            }
        finally:
            try:
                await client.disconnect()
            except:
                pass

        # Parse reflection results
        try:
            # Extract JSON from response (may be wrapped in markdown)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)

                # Structure the result
                return {
                    "observations": result.get("new_key_points", []),
                    "patterns": self._extract_patterns(result),
                    "evaluations": result.get("evaluations", []),
                    "raw_reflection": response_text
                }
            else:
                print("Warning: No JSON found in reflection response", file=sys.stderr)
                return {
                    "observations": [],
                    "patterns": [],
                    "evaluations": [],
                    "raw_reflection": response_text
                }

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse reflection JSON: {e}", file=sys.stderr)
            return {
                "observations": [],
                "patterns": [],
                "evaluations": [],
                "raw_reflection": response_text,
                "parse_error": str(e)
            }

    def _extract_patterns(self, reflection_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract behavioral patterns from reflection data.

        Patterns are high-level observations that might span multiple key points.

        Args:
            reflection_data: Parsed reflection JSON

        Returns:
            List of identified patterns
        """
        patterns = []

        new_key_points = reflection_data.get("new_key_points", [])

        # Group related key points into patterns
        # For now, just convert each key point to a pattern
        # In future, could use clustering or LLM to identify higher-level patterns
        for kp in new_key_points:
            if isinstance(kp, dict):
                patterns.append({
                    "type": "specific",
                    "text": kp.get("text", ""),
                    "atomicity_score": kp.get("atomicity_score", 0),
                    "evidence": kp.get("evidence", "")
                })

        return patterns

    def evaluate_playbook(self,
                         playbook: Dict[str, Any],
                         evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply evaluation feedback to playbook items.

        Args:
            playbook: Current playbook
            evaluations: List of evaluations from reflection

        Returns:
            Summary of evaluations (helpful/neutral/harmful counts)
        """
        summary = {
            "helpful": 0,
            "neutral": 0,
            "harmful": 0,
            "total_evaluated": len(evaluations)
        }

        for eval_item in evaluations:
            rating = eval_item.get("rating", "neutral")
            summary[rating] = summary.get(rating, 0) + 1

        return summary
