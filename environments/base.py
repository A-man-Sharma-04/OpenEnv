"""
Base Environment Class for Mini RL Platform
Gym-style interface with reset, step, render methods.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel


class Action(BaseModel):
    """Generic action structure"""
    pass


class Observation(BaseModel):
    """Generic observation structure"""
    pass


class Reward(BaseModel):
    """Reward structure with score and feedback"""
    score: float
    feedback: str
    components: Optional[Dict[str, float]] = None  # rule, heuristic, llm scores


class BaseEnvironment(ABC):
    """
    Abstract base class for RL environments.
    Follows Gym-style interface.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state: Dict[str, Any] = {}
        self.max_steps = config.get('max_steps', 100)
        self.current_step = 0
        self.done = False

    @abstractmethod
    def reset(self) -> Observation:
        """Reset environment to initial state"""
        self.current_step = 0
        self.done = False
        self.state = self._get_initial_state()
        return self._get_observation()

    @abstractmethod
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
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

    @abstractmethod
    def render(self, mode: str = 'human') -> Optional[str]:
        """Render environment state"""
        pass

    @abstractmethod
    def _get_initial_state(self) -> Dict[str, Any]:
        """Get initial environment state"""
        pass

    @abstractmethod
    def _update_state(self, action: Action) -> None:
        """Update environment state based on action"""
        pass

    @abstractmethod
    def _get_observation(self) -> Observation:
        """Get current observation from state"""
        pass

    @abstractmethod
    def _calculate_reward(self, action: Action) -> Reward:
        """Calculate reward for the action"""
        pass

    @abstractmethod
    def _is_done(self) -> bool:
        """Check if episode should end"""
        pass

    def _get_done_reason(self) -> str:
        """Get reason for episode ending"""
        if self.current_step >= self.max_steps:
            return "max_steps_reached"
        return "task_completed"

    def get_action_space(self) -> Dict[str, Any]:
        """Get action space description"""
        return {}

    def get_observation_space(self) -> Dict[str, Any]:
        """Get observation space description"""
        return {}

    def close(self) -> None:
        """Clean up environment resources"""
        pass