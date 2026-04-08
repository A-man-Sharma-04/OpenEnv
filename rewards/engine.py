"""
Hybrid Reward Engine
Combines rule-based, heuristic, and LLM-based scoring.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from environments.base import Action, Reward
import asyncio
import re


class BaseGrader(ABC):
    """Base class for reward graders"""

    @abstractmethod
    async def grade(self, action: Action, context: Dict[str, Any]) -> Tuple[float, str]:
        """Grade the action and return (score, feedback)"""
        pass


class RuleBasedGrader(BaseGrader):
    """Deterministic rule-based grading"""

    async def grade(self, action: Action, context: Dict[str, Any]) -> Tuple[float, str]:
        # Implement specific rules based on environment
        env_type = context.get('env_type', '')

        if env_type == 'grid_world':
            return self._grade_grid_world(action, context)
        elif env_type == 'text_decision':
            return self._grade_text_decision(action, context)
        elif env_type == 'code_logic':
            return self._grade_code_logic(action, context)

        return 0.0, "No rule-based grading available"

    def _grade_grid_world(self, action, context):
        # Goal reached check
        if context.get('goal_reached', False):
            return 1.0, "Goal reached successfully"
        return 0.0, "Goal not reached"

    def _grade_text_decision(self, action, context):
        correct_decision = context.get('correct_decision', '')
        if hasattr(action, 'decision') and action.decision == correct_decision:
            return 1.0, "Correct decision"
        return 0.0, "Incorrect decision"

    def _grade_code_logic(self, action, context):
        solution = getattr(action, 'solution', '').lower()
        keywords = context.get('solution_keywords', [])
        matched = sum(1 for kw in keywords if kw.lower() in solution)
        score = min(1.0, matched / len(keywords)) if keywords else 0.0
        return score, f"Matched {matched}/{len(keywords)} keywords"


class HeuristicGrader(BaseGrader):
    """Heuristic-based grading for efficiency and quality"""

    async def grade(self, action: Action, context: Dict[str, Any]) -> Tuple[float, str]:
        env_type = context.get('env_type', '')

        if env_type == 'grid_world':
            return self._grade_grid_world(action, context)
        elif env_type == 'text_decision':
            return self._grade_text_decision(action, context)
        elif env_type == 'code_logic':
            return self._grade_code_logic(action, context)

        return 0.5, "Default heuristic score"

    def _grade_grid_world(self, action, context):
        # Penalize for steps taken and distance to goal
        steps = context.get('steps', 0)
        distance = context.get('distance_to_goal', 0)
        penalty = (steps * 0.1) + (distance * 0.2)
        score = max(0.0, 1.0 - penalty)
        return score, f"Efficiency score: {score:.2f}"

    def _grade_text_decision(self, action, context):
        # Score based on reasoning quality
        reasoning = getattr(action, 'reasoning', '') or ''
        score = min(1.0, len(reasoning.split()) / 50)  # Length-based heuristic
        return score, f"Reasoning quality: {score:.2f}"

    def _grade_code_logic(self, action, context):
        # Score based on solution completeness
        solution = getattr(action, 'solution', '')
        confidence = getattr(action, 'confidence', 0.5)
        length_score = min(1.0, len(solution.split()) / 30)
        score = (length_score + confidence) / 2
        return score, f"Solution completeness: {score:.2f}"


class LLMGrader(BaseGrader):
    """LLM-based qualitative evaluation"""

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    async def grade(self, action: Action, context: Dict[str, Any]) -> Tuple[float, str]:
        env_type = context.get('env_type', '')

        # Generate prompt based on environment
        prompt = self._generate_prompt(action, context, env_type)

        try:
            response = await self.llm_provider.generate(prompt)
            score, feedback = self._parse_response(response)
            return score, feedback
        except Exception as e:
            return 0.5, f"LLM grading failed: {str(e)}"

    def _generate_prompt(self, action, context, env_type):
        if env_type == 'grid_world':
            return f"""
Evaluate this grid world navigation action:
Action: Move {getattr(action, 'direction', 'unknown')}
Context: Agent at {context.get('agent_pos', 'unknown')}, goal at {context.get('goal_pos', 'unknown')}
Steps taken: {context.get('steps', 0)}

Rate the action's quality from 0.0 to 1.0 considering:
- Progress toward goal
- Efficiency
- Strategic thinking

Return JSON: {{"score": 0.85, "reasoning": "Good progress toward goal", "confidence": 0.9}}
"""
        elif env_type == 'text_decision':
            return f"""
Evaluate this decision-making action:
Decision: {getattr(action, 'decision', 'unknown')}
Reasoning: {getattr(action, 'reasoning', 'none provided')}
Scenario: {context.get('scenario', '')}

Rate the decision quality from 0.0 to 1.0 considering:
- Logical reasoning
- Completeness of thought process
- Appropriateness for scenario

Return JSON: {{"score": 0.75, "reasoning": "Solid reasoning with good analysis", "confidence": 0.8}}
"""
        elif env_type == 'code_logic':
            return f"""
Evaluate this code/logic solution:
Task: {context.get('task_type', 'unknown')}
Solution: {getattr(action, 'solution', '')}
Problem: {context.get('problem', '')}

Rate the solution quality from 0.0 to 1.0 considering:
- Correctness
- Code quality/style
- Completeness

Return JSON: {{"score": 0.9, "reasoning": "Excellent solution with proper syntax", "confidence": 0.95}}
"""
        return "Generic evaluation prompt"

    def _parse_response(self, response: str) -> Tuple[float, str]:
        try:
            import json
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get('score', 0.5))
                reasoning = data.get('reasoning', 'No reasoning provided')
                return score, reasoning
        except:
            pass

        # Fallback: extract score from text
        import re
        score_match = re.search(r'score["\s:]*([0-9.]+)', response, re.IGNORECASE)
        if score_match:
            return float(score_match.group(1)), "Extracted from response"

        return 0.5, "Could not parse LLM response"


class RewardEngine:
    """Combines multiple grading approaches"""

    def __init__(self, llm_provider=None, weights: Optional[Dict[str, float]] = None):
        self.rule_grader = RuleBasedGrader()
        self.heuristic_grader = HeuristicGrader()
        self.llm_grader = LLMGrader(llm_provider) if llm_provider else None

        # Default weights
        self.weights = weights or {
            'rule': 0.4,
            'heuristic': 0.3,
            'llm': 0.3
        }

    async def calculate_reward(self, action: Action, context: Dict[str, Any]) -> Reward:
        """Calculate hybrid reward"""

        # Get individual scores
        rule_score, rule_feedback = await self.rule_grader.grade(action, context)
        heuristic_score, heuristic_feedback = await self.heuristic_grader.grade(action, context)

        llm_score, llm_feedback = 0.0, "LLM not available"
        if self.llm_grader:
            llm_score, llm_feedback = await self.llm_grader.grade(action, context)

        # Weighted combination
        total_score = (
            self.weights['rule'] * rule_score +
            self.weights['heuristic'] * heuristic_score +
            self.weights['llm'] * llm_score
        )

        # Combine feedback
        feedback = f"Rule: {rule_feedback} | Heuristic: {heuristic_feedback} | LLM: {llm_feedback}"

        return Reward(
            score=total_score,
            feedback=feedback,
            components={
                'rule': rule_score,
                'heuristic': heuristic_score,
                'llm': llm_score
            }
        )