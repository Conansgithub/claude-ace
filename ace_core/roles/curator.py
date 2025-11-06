#!/usr/bin/env python3
"""
Claude ACE - Curator Role
Converts reflection insights into actionable playbook strategies.
Corresponds to the Curator component in the ACE framework.
"""
import json
from typing import List, Dict, Any
from datetime import datetime


class Curator:
    """
    Curator transforms reflection observations into playbook updates.

    In the ACE framework, the Curator's job is to:
    1. Convert raw observations into reusable strategies
    2. Ensure key points are atomic and actionable
    3. Filter out low-quality or redundant learnings
    4. Structure updates as deltas
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Curator.

        Args:
            config: ACE configuration with quality thresholds
        """
        self.config = config
        self.min_atomicity = config.get("reflection", {}).get("min_atomicity_score", 0.70)

    def curate(self,
              reflection_result: Dict[str, Any],
              existing_playbook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Curate reflection observations into playbook updates.

        Args:
            reflection_result: Output from Reflector
            existing_playbook: Current playbook

        Returns:
            Dictionary with:
            - new_key_points: List of curated key points to add
            - evaluations: Score updates for existing points
            - rejected: List of rejected observations with reasons
        """
        observations = reflection_result.get("observations", [])
        evaluations = reflection_result.get("evaluations", [])
        patterns = reflection_result.get("patterns", [])

        # Curate new key points
        curated_points = []
        rejected_points = []

        existing_texts = {
            kp["text"].lower().strip()
            for kp in existing_playbook.get("key_points", [])
            if kp.get("status") != "archived"
        }

        for obs in observations:
            if isinstance(obs, str):
                # Old format: just text
                if obs.lower().strip() in existing_texts:
                    rejected_points.append({
                        "text": obs,
                        "reason": "duplicate"
                    })
                    continue

                curated_points.append({
                    "text": obs,
                    "atomicity_score": None
                })

            elif isinstance(obs, dict):
                text = obs.get("text", "")
                atomicity_score = obs.get("atomicity_score", 1.0)
                evidence = obs.get("evidence", "")

                # Quality filter: atomicity score
                if atomicity_score is not None and atomicity_score < self.min_atomicity:
                    rejected_points.append({
                        "text": text,
                        "atomicity_score": atomicity_score,
                        "reason": f"atomicity_score {atomicity_score:.2f} below threshold {self.min_atomicity}"
                    })
                    continue

                # Duplicate check
                if text.lower().strip() in existing_texts:
                    rejected_points.append({
                        "text": text,
                        "reason": "duplicate"
                    })
                    continue

                # Quality filter: must be specific and actionable
                if not self._is_quality_keypoint(text):
                    rejected_points.append({
                        "text": text,
                        "reason": "too vague or generic"
                    })
                    continue

                # Accepted
                curated_points.append({
                    "text": text,
                    "atomicity_score": atomicity_score,
                    "evidence": evidence
                })

                # Add to existing texts to prevent duplicates within this batch
                existing_texts.add(text.lower().strip())

        return {
            "new_key_points": curated_points,
            "evaluations": evaluations,
            "rejected": rejected_points,
            "curation_summary": {
                "observations_processed": len(observations),
                "accepted": len(curated_points),
                "rejected": len(rejected_points),
                "evaluations": len(evaluations)
            }
        }

    def _is_quality_keypoint(self, text: str) -> bool:
        """
        Check if a key point meets quality standards.

        Args:
            text: Key point text

        Returns:
            True if meets quality standards
        """
        text_lower = text.lower()

        # Reject if too short (likely incomplete)
        if len(text) < 20:
            return False

        # Reject if too long (likely not atomic)
        if len(text) > 300:
            return False

        # Reject generic advice (common anti-patterns)
        generic_patterns = [
            "be helpful",
            "be clear",
            "be concise",
            "understand context",
            "user wants",
            "provide good",
            "make sure",
            "always try",
            "something",
            "various",
            "sometimes"
        ]

        for pattern in generic_patterns:
            if pattern in text_lower:
                return False

        # Require specific indicators (at least one)
        specific_indicators = [
            "use",
            "when",
            "if",
            "check",
            "run",
            "call",
            "read",
            "write",
            "create",
            "update",
            "delete",
            "prefer",
            "avoid",
            ".py",
            ".js",
            ".ts",
            "command",
            "tool",
            "function",
            "file",
            "directory"
        ]

        has_specific = any(indicator in text_lower for indicator in specific_indicators)
        if not has_specific:
            return False

        return True

    def merge_patterns(self,
                      patterns: List[Dict[str, Any]],
                      max_patterns: int = 5) -> List[Dict[str, Any]]:
        """
        Merge similar patterns into higher-level strategies.

        Args:
            patterns: List of patterns from Reflector
            max_patterns: Maximum number of patterns to return

        Returns:
            Merged and prioritized patterns
        """
        # For now, just sort by atomicity score and take top N
        # In future, could use clustering or LLM to merge similar patterns

        sorted_patterns = sorted(
            patterns,
            key=lambda x: x.get("atomicity_score", 0),
            reverse=True
        )

        return sorted_patterns[:max_patterns]

    def create_learning_summary(self,
                               curated_result: Dict[str, Any]) -> str:
        """
        Create a human-readable summary of learning.

        Args:
            curated_result: Output from curate()

        Returns:
            Formatted summary string
        """
        summary = curated_result.get("curation_summary", {})

        lines = [
            f"📚 Learning Summary:",
            f"  Processed: {summary.get('observations_processed', 0)} observations",
            f"  ✅ Accepted: {summary.get('accepted', 0)} new key points",
            f"  ❌ Rejected: {summary.get('rejected', 0)} (quality filters)",
            f"  📊 Evaluated: {summary.get('evaluations', 0)} existing points"
        ]

        # Show rejected reasons if any
        rejected = curated_result.get("rejected", [])
        if rejected:
            reasons = {}
            for item in rejected:
                reason = item.get("reason", "unknown")
                reasons[reason] = reasons.get(reason, 0) + 1

            lines.append("  Rejection reasons:")
            for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"    • {reason}: {count}")

        return "\n".join(lines)
