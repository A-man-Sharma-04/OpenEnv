"""
Evaluation Pipeline
Runs agents on environments and collects metrics.
"""
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import json
import time
from environments.base import BaseEnvironment, Action, Observation, Reward
from agents.base import BaseAgent
from rewards.engine import RewardEngine


class EpisodeResult:
    """Result of a single episode"""

    def __init__(self):
        self.states: List[Observation] = []
        self.actions: List[Action] = []
        self.rewards: List[Reward] = []
        self.total_reward: float = 0.0
        self.steps: int = 0
        self.success: bool = False
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_reward': self.total_reward,
            'steps': self.steps,
            'success': self.success,
            'avg_reward': self.total_reward / self.steps if self.steps > 0 else 0,
            'metadata': self.metadata
        }


class EvaluationRunner:
    """Runs evaluation episodes"""

    def __init__(self, reward_engine: Optional[RewardEngine] = None):
        self.reward_engine = reward_engine

    async def run_episode(self, env: BaseEnvironment, agent: BaseAgent, max_steps: int = 100) -> EpisodeResult:
        """Run a single episode"""
        result = EpisodeResult()

        # Reset environment and agent
        observation = env.reset()
        agent.reset()

        result.states.append(observation)

        for step in range(max_steps):
            # Agent chooses action
            action = agent.act(observation)
            result.actions.append(action)

            # Environment step
            next_observation, reward, done, info = env.step(action)

            result.rewards.append(reward)
            result.total_reward += reward.score
            result.steps = step + 1

            # Agent learns (if learning agent)
            agent.learn(observation, action, reward.score, next_observation, done)

            # Update observation
            observation = next_observation
            result.states.append(observation)

            if done:
                result.success = True
                break

        result.metadata = {
            'final_state': observation.dict() if hasattr(observation, 'dict') else str(observation),
            'total_steps': result.steps,
            'avg_reward_per_step': result.total_reward / result.steps if result.steps > 0 else 0
        }

        return result

    async def run_multiple_episodes(self, env: BaseEnvironment, agent: BaseAgent,
                                   num_episodes: int = 10, max_steps: int = 100) -> List[EpisodeResult]:
        """Run multiple episodes"""
        results = []

        for episode in range(num_episodes):
            result = await self.run_episode(env, agent, max_steps)
            results.append(result)

        return results

    def calculate_metrics(self, results: List[EpisodeResult]) -> Dict[str, Any]:
        """Calculate aggregate metrics"""
        if not results:
            return {}

        total_rewards = [r.total_reward for r in results]
        steps = [r.steps for r in results]
        successes = [r.success for r in results]

        return {
            'num_episodes': len(results),
            'avg_total_reward': sum(total_rewards) / len(total_rewards),
            'std_total_reward': (sum((x - sum(total_rewards)/len(total_rewards))**2 for x in total_rewards) / len(total_rewards))**0.5,
            'avg_steps': sum(steps) / len(steps),
            'success_rate': sum(successes) / len(successes),
            'min_reward': min(total_rewards),
            'max_reward': max(total_rewards),
            'min_steps': min(steps),
            'max_steps': max(steps)
        }


class Leaderboard:
    """Manages agent performance rankings"""

    def __init__(self):
        self.scores: Dict[str, Dict[str, Any]] = {}

    def add_result(self, agent_name: str, env_name: str, metrics: Dict[str, Any]):
        """Add evaluation result"""
        if agent_name not in self.scores:
            self.scores[agent_name] = {}

        self.scores[agent_name][env_name] = metrics

    def get_rankings(self, env_name: str) -> List[Tuple[str, float]]:
        """Get agents ranked by performance on environment"""
        rankings = []

        for agent_name, env_scores in self.scores.items():
            if env_name in env_scores:
                score = env_scores[env_name].get('avg_total_reward', 0)
                rankings.append((agent_name, score))

        return sorted(rankings, key=lambda x: x[1], reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """Export leaderboard as dict"""
        return self.scores