#!/usr/bin/env python3
"""
Claude ACE - Delta Manager
Handles incremental updates to Playbook with history tracking
Prevents context collapse through delta-based operations
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class PlaybookDelta:
    """
    Represents a set of incremental changes to the Playbook.
    Follows the ACE framework's delta update principle.
    """

    def __init__(self, source: str = "unknown"):
        """
        Initialize a new delta.

        Args:
            source: Source of the delta (e.g., "precompact", "session_end")
        """
        self.timestamp = datetime.now().isoformat()
        self.source = source
        self.operations = []

    def add_keypoint(self, keypoint: Dict[str, Any], reason: str = ""):
        """
        Add a new key point.

        Args:
            keypoint: Key point dictionary with name, text, score
            reason: Reason for adding this key point
        """
        self.operations.append({
            "type": "add",
            "target": keypoint["name"],
            "data": keypoint,
            "reason": reason
        })

    def remove_keypoint(self, name: str, reason: str = ""):
        """
        Mark a key point for archival (soft delete).

        Args:
            name: Name of key point to archive
            reason: Reason for removal
        """
        self.operations.append({
            "type": "archive",
            "target": name,
            "reason": reason
        })

    def update_score(self, name: str, delta: int, rating: str, justification: str = ""):
        """
        Update key point score.

        Args:
            name: Key point name
            delta: Score change amount
            rating: Rating type (helpful/harmful/neutral)
            justification: Reason for score change
        """
        self.operations.append({
            "type": "score_update",
            "target": name,
            "delta": delta,
            "rating": rating,
            "justification": justification
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert delta to dictionary for storage"""
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "operations": self.operations,
            "operation_count": len(self.operations)
        }


class PlaybookHistory:
    """
    Manages Playbook evolution history.
    Enables rollback and analysis of learning progress.
    """

    def __init__(self, ace_dir: Path):
        """
        Initialize history manager.

        Args:
            ace_dir: Path to .claude directory
        """
        self.ace_dir = ace_dir
        self.history_file = ace_dir / "playbook_history.jsonl"

    def record_delta(self, delta: PlaybookDelta, playbook_snapshot: Dict[str, Any]):
        """
        Record a delta to history.

        Args:
            delta: Delta object to record
            playbook_snapshot: Current state of playbook after delta
        """
        # Ensure directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        history_entry = {
            **delta.to_dict(),
            "playbook_size": len(playbook_snapshot.get("key_points", [])),
            "avg_score": self._calculate_avg_score(playbook_snapshot)
        }

        # Append to JSONL file
        with open(self.history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(history_entry, ensure_ascii=False) + '\n')

    def get_recent_deltas(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent delta history.

        Args:
            limit: Maximum number of deltas to return

        Returns:
            List of delta dictionaries
        """
        if not self.history_file.exists():
            return []

        deltas = []
        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    deltas.append(json.loads(line))

        # Return most recent
        return deltas[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Playbook evolution.

        Returns:
            Statistics dictionary
        """
        if not self.history_file.exists():
            return {
                "total_updates": 0,
                "total_additions": 0,
                "total_archival": 0,
                "total_score_updates": 0
            }

        stats = {
            "total_updates": 0,
            "total_additions": 0,
            "total_archival": 0,
            "total_score_updates": 0,
            "updates_by_source": {}
        }

        with open(self.history_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                delta = json.loads(line)
                stats["total_updates"] += 1

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

        return stats

    def _calculate_avg_score(self, playbook: Dict[str, Any]) -> float:
        """Calculate average score of active key points"""
        key_points = playbook.get("key_points", [])
        if not key_points:
            return 0.0

        # Only count active (non-archived) points
        active_points = [kp for kp in key_points if kp.get("status") != "archived"]
        if not active_points:
            return 0.0

        total_score = sum(kp.get("score", 0) for kp in active_points)
        return total_score / len(active_points)


def apply_delta(playbook: Dict[str, Any], delta: PlaybookDelta) -> Dict[str, Any]:
    """
    Apply delta operations to playbook.
    Uses incremental updates instead of full replacement.

    Args:
        playbook: Current playbook
        delta: Delta operations to apply

    Returns:
        Updated playbook
    """
    # Create name to keypoint mapping for efficient lookup
    name_to_kp = {kp["name"]: kp for kp in playbook["key_points"]}

    for operation in delta.operations:
        op_type = operation["type"]
        target = operation["target"]

        if op_type == "add":
            # Add new key point
            new_kp = operation["data"]
            if target not in name_to_kp:
                # Add metadata
                new_kp["created_at"] = delta.timestamp
                new_kp["status"] = "active"
                new_kp["reason"] = operation.get("reason", "")
                playbook["key_points"].append(new_kp)
                name_to_kp[target] = new_kp

        elif op_type == "archive":
            # Soft delete: mark as archived instead of removing
            if target in name_to_kp:
                name_to_kp[target]["status"] = "archived"
                name_to_kp[target]["archived_at"] = delta.timestamp
                name_to_kp[target]["archive_reason"] = operation.get("reason", "")

        elif op_type == "score_update":
            # Update score with history
            if target in name_to_kp:
                kp = name_to_kp[target]
                old_score = kp.get("score", 0)
                kp["score"] = old_score + operation["delta"]

                # Record evaluation history
                if "evaluations" not in kp:
                    kp["evaluations"] = []
                kp["evaluations"].append({
                    "timestamp": delta.timestamp,
                    "rating": operation["rating"],
                    "delta": operation["delta"],
                    "justification": operation.get("justification", ""),
                    "old_score": old_score,
                    "new_score": kp["score"]
                })

    # Update metadata
    playbook["last_updated"] = delta.timestamp
    playbook["last_delta_source"] = delta.source

    return playbook


def cleanup_archived_points(playbook: Dict[str, Any],
                           days_threshold: int = 30,
                           keep_recent: int = 5) -> Dict[str, Any]:
    """
    Clean up old archived points.
    Only removes points that have been archived for a long time.

    Args:
        playbook: Current playbook
        days_threshold: Days before archived points can be permanently removed
        keep_recent: Number of recent archived points to always keep

    Returns:
        Cleaned playbook
    """
    from datetime import timedelta

    now = datetime.now()
    threshold_date = now - timedelta(days=days_threshold)

    archived_points = [
        kp for kp in playbook["key_points"]
        if kp.get("status") == "archived"
    ]

    # Sort by archive date (most recent first)
    archived_points.sort(
        key=lambda x: x.get("archived_at", ""),
        reverse=True
    )

    # Keep recent archived points
    keep_archived = set(kp["name"] for kp in archived_points[:keep_recent])

    # Filter key points
    cleaned_points = []
    for kp in playbook["key_points"]:
        # Keep active points
        if kp.get("status") != "archived":
            cleaned_points.append(kp)
            continue

        # Keep recent archived points
        if kp["name"] in keep_archived:
            cleaned_points.append(kp)
            continue

        # Check if old enough to remove
        archived_at = kp.get("archived_at")
        if archived_at:
            try:
                archived_date = datetime.fromisoformat(archived_at)
                if archived_date > threshold_date:
                    # Not old enough, keep it
                    cleaned_points.append(kp)
            except (ValueError, TypeError):
                # Keep if we can't parse the date
                cleaned_points.append(kp)

    playbook["key_points"] = cleaned_points
    return playbook
