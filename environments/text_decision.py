"""
Text Decision Environment
Multi-step reasoning task where agent makes decisions based on text.
"""
from typing import Any, Dict, List, Optional, Tuple
from environments.base import BaseEnvironment, Action, Observation, Reward
from pydantic import BaseModel


class TextAction(Action):
    decision: str  # 'yes', 'no', 'maybe'
    reasoning: Optional[str] = None


class TextObservation(Observation):
    scenario: str
    question: str
    history: List[Dict[str, str]]
    step_count: int


class TextDecisionEnv(BaseEnvironment):
    """
    Text-based decision making environment.
    Agent reads scenarios and makes reasoned decisions.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.scenarios = config.get('scenarios', self._default_scenarios())
        self.current_scenario_idx = 0

    def reset(self) -> TextObservation:
        """Reset environment to initial state"""
        self.current_step = 0
        self.done = False
        self.state = self._get_initial_state()
        return self._get_observation()

    def step(self, action: TextAction) -> Tuple[TextObservation, Reward, bool, Dict[str, Any]]:
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

    def _default_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                'scenario': 'You are a project manager. A team member requests 2 weeks extension on a critical deadline due to personal reasons.',
                'question': 'Should you grant the extension?',
                'correct_decision': 'yes',
                'reasoning_keywords': ['compassion', 'retention', 'flexibility']
            },
            {
                'scenario': 'As a doctor, you have a patient who needs emergency surgery but refuses due to religious beliefs.',
                'question': 'Should you proceed with the surgery?',
                'correct_decision': 'no',
                'reasoning_keywords': ['autonomy', 'consent', 'ethics']
            },
            {
                'scenario': 'You are an investor considering a startup with innovative technology but inexperienced management.',
                'question': 'Should you invest?',
                'correct_decision': 'maybe',
                'reasoning_keywords': ['risk', 'potential', 'due diligence']
            }
        ]

    def _get_initial_state(self) -> Dict[str, Any]:
        scenario = self.scenarios[self.current_scenario_idx]
        return {
            'scenario': scenario,
            'decisions': [],
            'step_count': 0
        }

    def _update_state(self, action: TextAction) -> None:
        self.state['decisions'].append({
            'decision': action.decision,
            'reasoning': action.reasoning or '',
            'step': str(self.state['step_count'])
        })
        self.state['step_count'] += 1

    def _get_observation(self) -> TextObservation:
        scenario = self.state['scenario']
        return TextObservation(
            scenario=scenario['scenario'],
            question=scenario['question'],
            history=self.state['decisions'],
            step_count=self.state['step_count']
        )

    def _calculate_reward(self, action: TextAction) -> Reward:
        scenario = self.state['scenario']
        correct_decision = scenario['correct_decision']

        # Rule-based: correct decision
        rule_score = 1.0 if action.decision == correct_decision else 0.0

        # Heuristic: reasoning quality
        heuristic_score = 0.0
        if action.reasoning:
            reasoning_lower = action.reasoning.lower()
            keywords = scenario.get('reasoning_keywords', [])
            matched_keywords = sum(1 for kw in keywords if kw in reasoning_lower)
            heuristic_score = min(1.0, matched_keywords / len(keywords)) if keywords else 0.5

        # LLM score would be calculated separately
        llm_score = 0.0  # Placeholder

        # Weights: 0.4 rule, 0.3 heuristic, 0.3 llm
        total_score = 0.4 * rule_score + 0.3 * heuristic_score + 0.3 * llm_score

        feedback = f"Decision: {action.decision}"
        if action.decision == correct_decision:
            feedback += " ✓"
        else:
            feedback += f" (correct: {correct_decision})"

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
        # Single decision per scenario
        return self.state['step_count'] >= 1

    def render(self, mode: str = 'human') -> Optional[str]:
        obs = self._get_observation()
        output = f"Scenario: {obs.scenario}\n"
        output += f"Question: {obs.question}\n"
        if obs.history:
            output += f"Decision: {obs.history[-1]['decision']}\n"
            if obs.history[-1]['reasoning']:
                output += f"Reasoning: {obs.history[-1]['reasoning']}\n"
        return output

    def get_action_space(self) -> Dict[str, Any]:
        return {
            'type': 'discrete',
            'actions': ['yes', 'no', 'maybe'],
            'reasoning': {'type': 'text', 'optional': True}
        }

    def get_observation_space(self) -> Dict[str, Any]:
        return {
            'scenario': {'type': 'str'},
            'question': {'type': 'str'},
            'history': {'type': 'list[dict]'},
            'step_count': {'type': 'int'}
        }