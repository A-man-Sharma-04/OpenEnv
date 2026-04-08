"""
Agent Base Classes and Implementations
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from environments.base import Action, Observation


class BaseAgent(ABC):
    """Base agent interface"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        """Choose action based on observation"""
        pass

    @abstractmethod
    def learn(self, observation: Observation, action: Action, reward: float, next_observation: Observation, done: bool) -> None:
        """Learn from experience (optional for non-learning agents)"""
        pass

    def reset(self) -> None:
        """Reset agent state"""
        pass


class RandomAgent(BaseAgent):
    """Random action selection agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.action_space = config.get('action_space', {})
        self.env_type = config.get('env_type', 'grid_world')  # Default fallback

    def act(self, observation: Observation) -> Action:
        """Choose random action based on environment type"""
        if hasattr(observation, 'grid'):  # Grid world
            from environments.grid_world import GridAction
            import random
            return GridAction(direction=random.choice(['up', 'down', 'left', 'right']))
        elif hasattr(observation, 'question'):  # Text decision
            from environments.text_decision import TextAction
            import random
            return TextAction(decision=random.choice(['yes', 'no', 'maybe']))
        elif hasattr(observation, 'code'):  # Code logic
            from environments.code_logic import CodeAction
            return CodeAction(task_type='general', solution='Random attempt', confidence=0.5)
        else:
            # Fallback
            from environments.grid_world import GridAction
            import random
            return GridAction(direction=random.choice(['up', 'down', 'left', 'right']))

    def learn(self, observation: Observation, action: Action, reward: float, next_observation: Observation, done: bool) -> None:
        pass  # No learning




class RuleBasedAgent(BaseAgent):
    """Rule-based agent with hardcoded logic"""

    def act(self, observation: Observation) -> Action:
        # Implement simple rules based on observation type
        if hasattr(observation, 'agent_pos') and hasattr(observation, 'goal_pos'):
            # Grid world logic
            from environments.grid_world import GridAction
            agent_x, agent_y = observation.agent_pos
            goal_x, goal_y = observation.goal_pos

            if agent_x < goal_x:
                direction = 'down'
            elif agent_x > goal_x:
                direction = 'up'
            elif agent_y < goal_y:
                direction = 'right'
            else:
                direction = 'left'

            return GridAction(direction=direction)

        elif hasattr(observation, 'question'):
            # Text decision logic
            from environments.text_decision import TextAction
            # Simple rule: always say "yes" with basic reasoning
            return TextAction(
                decision='yes',
                reasoning='Based on general principles, this seems like a reasonable choice.'
            )

        elif hasattr(observation, 'code'):
            # Code logic - simple bug fix attempt
            from environments.code_logic import CodeAction
            code = observation.code
            if 'for num in numbers' in code and ':' not in code.split('for num in numbers')[1].split('\n')[0]:
                solution = "Add colon ':' after 'for num in numbers'"
            else:
                solution = "General code improvement suggestion"

            return CodeAction(
                task_type=observation.task_type,
                solution=solution,
                confidence=0.7
            )

        # Fallback
        from environments.grid_world import GridAction
        return GridAction(direction='right')

    def learn(self, observation: Observation, action: Action, reward: float, next_observation: Observation, done: bool) -> None:
        pass  # No learning


class QLearningAgent(BaseAgent):
    """Simple Q-learning agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.alpha = config.get('alpha', 0.1)  # Learning rate
        self.gamma = config.get('gamma', 0.9)  # Discount factor
        self.epsilon = config.get('epsilon', 0.1)  # Exploration rate
        self.q_table: Dict[str, Dict[str, float]] = {}

    def _get_state_key(self, observation: Observation) -> str:
        """Convert observation to state key"""
        if hasattr(observation, 'agent_pos'):
            return f"grid_{observation.agent_pos}"
        elif hasattr(observation, 'step_count'):
            return f"step_{observation.step_count}"
        else:
            return "default"

    def _get_action_key(self, action: Action) -> str:
        """Convert action to action key"""
        if hasattr(action, 'direction'):
            return action.direction
        elif hasattr(action, 'decision'):
            return action.decision
        elif hasattr(action, 'solution'):
            return "solution_provided"
        return "default"

    def act(self, observation: Observation) -> Action:
        state_key = self._get_state_key(observation)

        # Initialize Q-values for new state
        if state_key not in self.q_table:
            self.q_table[state_key] = {}

        # Epsilon-greedy action selection
        import random
        if random.random() < self.epsilon:
            # Explore: random action
            return self._get_random_action(observation)
        else:
            # Exploit: best action
            actions = self.q_table[state_key]
            if not actions:
                return self._get_random_action(observation)

            best_action_key = max(actions, key=actions.get)
            return self._action_from_key(best_action_key, observation)

    def learn(self, observation: Observation, action: Action, reward: float, next_observation: Observation, done: bool) -> None:
        state_key = self._get_state_key(observation)
        next_state_key = self._get_state_key(next_observation)
        action_key = self._get_action_key(action)

        # Initialize Q-values
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = {}

        # Q-learning update
        current_q = self.q_table[state_key].get(action_key, 0.0)

        if done:
            max_next_q = 0.0
        else:
            next_actions = self.q_table[next_state_key]
            max_next_q = max(next_actions.values()) if next_actions else 0.0

        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state_key][action_key] = new_q

    def _get_random_action(self, observation: Observation) -> Action:
        """Get a random valid action for the observation type"""
        if hasattr(observation, 'agent_pos'):
            from environments.grid_world import GridAction
            import random
            return GridAction(direction=random.choice(['up', 'down', 'left', 'right']))
        elif hasattr(observation, 'question'):
            from environments.text_decision import TextAction
            import random
            return TextAction(decision=random.choice(['yes', 'no', 'maybe']))
        else:
            from environments.code_logic import CodeAction
            return CodeAction(task_type='general', solution='Random attempt', confidence=0.5)

    def _action_from_key(self, action_key: str, observation: Observation) -> Action:
        """Convert action key back to Action object"""
        if hasattr(observation, 'agent_pos'):
            from environments.grid_world import GridAction
            return GridAction(direction=action_key)
        elif hasattr(observation, 'question'):
            from environments.text_decision import TextAction
            return TextAction(decision=action_key)
        else:
            from environments.code_logic import CodeAction
            return CodeAction(task_type='general', solution='Learned solution', confidence=0.8)