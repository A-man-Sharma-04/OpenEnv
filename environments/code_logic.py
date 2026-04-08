"""
Code/Logic Task Environment
Agent solves coding problems or logical puzzles.
"""
from typing import Any, Dict, List, Optional, Tuple
from environments.base import BaseEnvironment, Action, Observation, Reward
from pydantic import BaseModel
import random


class CodeAction(Action):
    task_type: str  # 'bug_fix', 'refactor', 'logic'
    solution: str
    confidence: float = 0.5


class CodeObservation(Observation):
    problem: str
    code: str
    task_type: str
    hints: Optional[List[str]] = None


class CodeLogicEnv(BaseEnvironment):
    """
    Code and logic problem solving environment.
    Agent analyzes code/logic problems and provides solutions.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.problems = config.get('problems', self._default_problems())

    def reset(self) -> CodeObservation:
        """Reset environment to initial state"""
        self.current_step = 0
        self.done = False
        self.state = self._get_initial_state()
        return self._get_observation()

    def step(self, action: CodeAction) -> Tuple[CodeObservation, Reward, bool, Dict[str, Any]]:
        """
        Execute action and return (observation, reward, done, info)
        """
        self.current_step += 1
        if self.current_step >= self.max_steps:
            self.done = True

        # Update state based on action
        self._update_state(action)

        # Get observation
        observation = self._get_observation()

        # Calculate reward
        reward = self._calculate_reward(action)

        # Check if episode is done
        self.done = self.done or self._is_done()

        info = {
            'step': self.current_step,
            'max_steps': self.max_steps,
            'done_reason': self._get_done_reason() if self.done else None
        }

        return observation, reward, self.done, info

    def _default_problems(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': 'bug_fix',
                'problem': 'Fix the syntax error in this Python function',
                'code': 'def calculate_sum(numbers):\n    total = 0\n    for num in numbers\n        total += num\n    return total',
                'solution_keywords': ['colon', 'for loop', ':'],
                'correct_solution': 'Add colon after for num in numbers'
            },
            {
                'id': 'refactor',
                'problem': 'Refactor this code to use list comprehension',
                'code': 'def get_even_numbers(nums):\n    evens = []\n    for n in nums:\n        if n % 2 == 0:\n            evens.append(n)\n    return evens',
                'solution_keywords': ['list comprehension', '[n for n in nums if n % 2 == 0]'],
                'correct_solution': 'return [n for n in nums if n % 2 == 0]'
            },
            {
                'id': 'logic',
                'problem': 'Solve this logical puzzle: If all bloops are razzes and some razzes are fizzles, are all bloops fizzles?',
                'code': '',
                'solution_keywords': ['no', 'not necessarily', 'some'],
                'correct_solution': 'No, not all bloops are necessarily fizzles'
            }
        ]

    def _get_initial_state(self) -> Dict[str, Any]:
        problem = random.choice(self.problems)
        return {
            'problem': problem,
            'attempted': False,
            'step_count': 0
        }

    def _update_state(self, action: CodeAction) -> None:
        self.state['attempted'] = True
        self.state['last_action'] = action
        self.state['step_count'] += 1

    def _get_observation(self) -> CodeObservation:
        problem = self.state['problem']
        return CodeObservation(
            problem=problem['problem'],
            code=problem['code'],
            task_type=problem['id'],
            hints=problem.get('hints', [])
        )

    def _calculate_reward(self, action: CodeAction) -> Reward:
        problem = self.state['problem']
        solution_lower = action.solution.lower()

        # Rule-based scoring
        rule_score = 0.0
        keywords = problem.get('solution_keywords', [])
        if keywords:
            matched = sum(1 for kw in keywords if kw.lower() in solution_lower)
            rule_score = min(1.0, matched / len(keywords))

        # Heuristic: solution length and confidence
        heuristic_score = min(1.0, len(action.solution.split()) / 20) * action.confidence

        # LLM score placeholder
        llm_score = 0.0

        # Weighted combination
        total_score = 0.5 * rule_score + 0.3 * heuristic_score + 0.2 * llm_score

        feedback = f"Task: {problem['id']}"
        if rule_score > 0.7:
            feedback += " - Good solution!"
        elif rule_score > 0.3:
            feedback += " - Partial credit"
        else:
            feedback += " - Needs improvement"

        return Reward(
            score=total_score,
            feedback=feedback,
            components={
                'rule': rule_score,
                'heuristic': heuristic_score,
                'llm': llm_score
            }
        )

    def _is_done(self) -> bool:
        return self.state.get('attempted', False)

    def render(self, mode: str = 'human') -> Optional[str]:
        obs = self._get_observation()
        output = f"Problem: {obs.problem}\n"
        if obs.code:
            output += f"Code:\n{obs.code}\n"
        output += f"Task Type: {obs.task_type}\n"
        if self.state.get('last_action'):
            action = self.state['last_action']
            output += f"Solution: {action.solution}\n"
        return output

    def get_action_space(self) -> Dict[str, Any]:
        return {
            'task_type': ['bug_fix', 'refactor', 'logic'],
            'solution': {'type': 'text'},
            'confidence': {'type': 'float', 'range': [0.0, 1.0]}
        }

    def get_observation_space(self) -> Dict[str, Any]:
        return {
            'problem': {'type': 'str'},
            'code': {'type': 'str'},
            'task_type': {'type': 'str'},
            'hints': {'type': 'list[str]', 'optional': True}
        }