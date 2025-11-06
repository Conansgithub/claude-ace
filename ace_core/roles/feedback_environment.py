#!/usr/bin/env python3
"""
Claude ACE - Feedback Environment
Provides external feedback for agent execution validation.
Corresponds to the Environment component in the ACE framework.
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class FeedbackEnvironment:
    """
    Environment provides external feedback on agent execution.

    In the ACE framework, the Environment's role is to:
    1. Evaluate agent outputs against ground truth (if available)
    2. Collect user feedback on quality
    3. Track success/failure patterns
    4. Provide structured feedback for reflection
    """

    def __init__(self, ace_dir: Path):
        """
        Initialize Feedback Environment.

        Args:
            ace_dir: Path to .claude directory for storing feedback
        """
        self.ace_dir = ace_dir
        self.feedback_file = ace_dir / "feedback.jsonl"

    def record_feedback(self,
                       session_id: str,
                       interaction_id: str,
                       feedback_type: str,
                       feedback_data: Dict[str, Any]):
        """
        Record external feedback for an interaction.

        Args:
            session_id: Session identifier
            interaction_id: Specific interaction identifier
            feedback_type: Type of feedback (user_rating, execution_result, ground_truth)
            feedback_data: Feedback details
        """
        # Ensure directory exists
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "interaction_id": interaction_id,
            "type": feedback_type,
            "data": feedback_data
        }

        # Append to feedback file
        with open(self.feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback_entry, ensure_ascii=False) + '\n')

    def get_session_feedback(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a session.

        Args:
            session_id: Session to retrieve feedback for

        Returns:
            List of feedback entries
        """
        if not self.feedback_file.exists():
            return []

        feedback_list = []
        with open(self.feedback_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = json.loads(line)
                if entry.get("session_id") == session_id:
                    feedback_list.append(entry)

        return feedback_list

    def evaluate_with_ground_truth(self,
                                   question: str,
                                   agent_answer: str,
                                   ground_truth: str) -> Dict[str, Any]:
        """
        Evaluate agent answer against ground truth.

        Args:
            question: The question asked
            agent_answer: Agent's response
            ground_truth: Expected correct answer

        Returns:
            Evaluation result
        """
        # Simple exact match (can be enhanced with fuzzy matching, LLM evaluation, etc.)
        exact_match = agent_answer.strip().lower() == ground_truth.strip().lower()

        # Check if agent answer contains ground truth
        contains_answer = ground_truth.strip().lower() in agent_answer.strip().lower()

        return {
            "success": exact_match or contains_answer,
            "exact_match": exact_match,
            "contains_answer": contains_answer,
            "question": question,
            "agent_answer": agent_answer,
            "ground_truth": ground_truth,
            "feedback": self._generate_feedback(exact_match, contains_answer)
        }

    def _generate_feedback(self, exact_match: bool, contains_answer: bool) -> str:
        """Generate feedback message based on evaluation"""
        if exact_match:
            return "✓ Exact match with ground truth"
        elif contains_answer:
            return "✓ Answer contains ground truth (with additional context)"
        else:
            return "✗ Answer does not match ground truth"

    def parse_user_feedback(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Parse user feedback from natural language.

        Users can mark feedback in conversations like:
        - "这个建议很有用 ✓"  → helpful
        - "这个不对 ✗"        → harmful
        - "Good advice ✓"    → helpful

        Args:
            user_input: User's message

        Returns:
            Parsed feedback or None if no feedback found
        """
        user_lower = user_input.lower().strip()

        # Positive feedback indicators
        positive_patterns = [
            ("✓", "helpful"),
            ("👍", "helpful"),
            ("很有用", "helpful"),
            ("有帮助", "helpful"),
            ("good advice", "helpful"),
            ("helpful", "helpful"),
            ("works well", "helpful"),
            ("correct", "helpful"),
        ]

        # Negative feedback indicators
        negative_patterns = [
            ("✗", "harmful"),
            ("👎", "harmful"),
            ("不对", "harmful"),
            ("错误", "harmful"),
            ("不好", "harmful"),
            ("wrong", "harmful"),
            ("incorrect", "harmful"),
            ("doesn't work", "harmful"),
        ]

        # Check patterns
        for pattern, rating in positive_patterns:
            if pattern in user_lower:
                return {
                    "rating": rating,
                    "source": "user_explicit",
                    "original_text": user_input
                }

        for pattern, rating in negative_patterns:
            if pattern in user_lower:
                return {
                    "rating": rating,
                    "source": "user_explicit",
                    "original_text": user_input
                }

        return None

    def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary of recent feedback.

        Args:
            days: Number of days to look back

        Returns:
            Summary statistics
        """
        from datetime import timedelta

        if not self.feedback_file.exists():
            return {
                "total_feedback": 0,
                "by_type": {},
                "recent_feedback": []
            }

        cutoff_date = datetime.now() - timedelta(days=days)
        summary = {
            "total_feedback": 0,
            "by_type": {},
            "positive_count": 0,
            "negative_count": 0,
            "recent_feedback": []
        }

        with open(self.feedback_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = json.loads(line)
                entry_date = datetime.fromisoformat(entry["timestamp"])

                if entry_date < cutoff_date:
                    continue

                summary["total_feedback"] += 1

                fb_type = entry.get("type", "unknown")
                summary["by_type"][fb_type] = summary["by_type"].get(fb_type, 0) + 1

                # Count positive/negative
                data = entry.get("data", {})
                if data.get("rating") == "helpful" or data.get("success"):
                    summary["positive_count"] += 1
                elif data.get("rating") == "harmful" or data.get("success") is False:
                    summary["negative_count"] += 1

                summary["recent_feedback"].append(entry)

        return summary


class SimpleFeedbackCollector:
    """
    Simple feedback collector that can be embedded in hooks.
    Watches for feedback markers in user messages.
    """

    def __init__(self, environment: FeedbackEnvironment):
        """
        Initialize collector.

        Args:
            environment: FeedbackEnvironment instance
        """
        self.environment = environment
        self.last_interaction_id = None

    def process_message(self,
                       session_id: str,
                       message: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Process a message to detect and record feedback.

        Args:
            session_id: Current session ID
            message: Message dict with role and content

        Returns:
            Detected feedback or None
        """
        if message.get("role") != "user":
            return None

        content = message.get("content", "")
        feedback = self.environment.parse_user_feedback(content)

        if feedback:
            # Generate interaction ID (could be improved with actual message IDs)
            interaction_id = f"{session_id}_{datetime.now().timestamp()}"

            self.environment.record_feedback(
                session_id=session_id,
                interaction_id=interaction_id,
                feedback_type="user_explicit",
                feedback_data=feedback
            )

            return feedback

        return None
