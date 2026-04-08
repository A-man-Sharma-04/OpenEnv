"""
Grid World Navigation Environment
Deterministic grid world where agent must navigate to goal.
"""
from typing import Any, Dict, List, Optional, Tuple
from environments.base import BaseEnvironment, Action, Observation, Reward
from pydantic import BaseModel


class GridAction(Action):
    direction: str  # 'up', 'down', 'left', 'right'


class GridObservation(Observation):
    grid: List[List[str]]
    agent_pos: Tuple[int, int]
    goal_pos: Tuple[int, int]
    step_count: int


class GridWorldEnv(BaseEnvironment):
    """
    Simple grid world navigation task.
    Agent starts at (0,0), goal at (size-1, size-1).
    Obstacles block paths. Agent gets reward 1.0 for reaching goal.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.size = config.get('size', 5)
        self.obstacles = [tuple(obs) for obs in config.get('obstacles', [])]  # Convert to tuples
        self.start_pos = tuple(config.get('start_pos', [0, 0]))  # Convert to tuple
        self.goal_pos = tuple(config.get('goal_pos', [self.size-1, self.size-1]))  # Convert to tuple

    def _get_initial_state(self) -> Dict[str, Any]:
        return {
            'agent_pos': self.start_pos,
            'step_count': 0,
            'visited': set([self.start_pos])
        }

    def reset(self) -> GridObservation:
        """Reset environment to initial state"""
        self.current_step = 0
        self.done = False
        self.state = self._get_initial_state()
        return self._get_observation()

    def step(self, action: GridAction) -> Tuple[GridObservation, Reward, bool, Dict[str, Any]]:
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

    def _update_state(self, action: GridAction) -> None:
        direction = action.direction
        x, y = self.state['agent_pos']

        # Calculate new position
        if direction == 'up':
            new_pos = (x-1, y)
        elif direction == 'down':
            new_pos = (x+1, y)
        elif direction == 'left':
            new_pos = (x, y-1)
        elif direction == 'right':
            new_pos = (x, y+1)
        else:
            return  # Invalid action

        # Check bounds
        if not (0 <= new_pos[0] < self.size and 0 <= new_pos[1] < self.size):
            return  # Out of bounds

        # Check obstacles
        if new_pos in self.obstacles:
            return  # Blocked

        # Update position
        self.state['agent_pos'] = new_pos
        self.state['visited'].add(new_pos)
        self.state['step_count'] += 1

    def _get_observation(self) -> GridObservation:
        grid = self._render_grid()
        return GridObservation(
            grid=grid,
            agent_pos=self.state['agent_pos'],
            goal_pos=self.goal_pos,
            step_count=self.state['step_count']
        )

    def _calculate_reward(self, action: GridAction) -> Reward:
        agent_pos = self.state['agent_pos']

        # Goal reached
        if agent_pos == self.goal_pos:
            return Reward(
                score=1.0,
                feedback="Goal reached!",
                components={'rule': 1.0, 'heuristic': 0.0, 'llm': 0.0}
            )

        # Heuristic: distance penalty
        dist = abs(agent_pos[0] - self.goal_pos[0]) + abs(agent_pos[1] - self.goal_pos[1])
        heuristic_penalty = dist * 0.1

        # Step penalty
        step_penalty = self.state['step_count'] * 0.01

        score = max(0.0, 0.5 - heuristic_penalty - step_penalty)

        return Reward(
            score=score,
            feedback=f"Moving {action.direction}, distance to goal: {dist}",
            components={'rule': 0.0, 'heuristic': score, 'llm': 0.0}
        )

    def _is_done(self) -> bool:
        return self.state['agent_pos'] == self.goal_pos

    def render(self, mode: str = 'human') -> Optional[str]:
        if mode == 'human':
            return '\n'.join([' '.join(row) for row in self._render_grid()])
        return None

    def _render_grid(self) -> List[List[str]]:
        grid = [['.' for _ in range(self.size)] for _ in range(self.size)]

        # Place obstacles
        for obs in self.obstacles:
            grid[obs[0]][obs[1]] = '#'

        # Place goal
        grid[self.goal_pos[0]][self.goal_pos[1]] = 'G'

        # Place agent
        agent_pos = self.state['agent_pos']
        grid[agent_pos[0]][agent_pos[1]] = 'A'

        return grid

    def get_action_space(self) -> Dict[str, Any]:
        return {
            'type': 'discrete',
            'actions': ['up', 'down', 'left', 'right']
        }

    def get_observation_space(self) -> Dict[str, Any]:
        return {
            'grid': {'shape': (self.size, self.size), 'type': 'str'},
            'agent_pos': {'type': 'tuple[int, int]'},
            'goal_pos': {'type': 'tuple[int, int]'},
            'step_count': {'type': 'int'}
        }