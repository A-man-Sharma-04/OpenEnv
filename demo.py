#!/usr/bin/env python3
"""
Demo Script for Mini RL Platform
Runs a complete evaluation pipeline with different agents and environments.
"""
import asyncio
import json
import os
from typing import Dict, Any
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Import our modules
from environments.grid_world import GridWorldEnv
from environments.text_decision import TextDecisionEnv
from environments.code_logic import CodeLogicEnv
from agents.base import RandomAgent, RuleBasedAgent, QLearningAgent
from evaluation.runner import EvaluationRunner, Leaderboard
from llm.provider import GroqProvider, LLMManager, MockProvider
from rewards.engine import RewardEngine


async def load_task_config(task_file: str) -> Dict[str, Any]:
    """Load task configuration from JSON file"""
    with open(f"tasks/{task_file}", 'r') as f:
        return json.load(f)


def create_environment_from_config(task_config: Dict[str, Any]):
    """Create environment from task config"""
    env_type = task_config['env_type']
    config = task_config['config']

    if env_type == 'grid_world':
        return GridWorldEnv(config)
    elif env_type == 'text_decision':
        return TextDecisionEnv(config)
    elif env_type == 'code_logic':
        return CodeLogicEnv(config)
    else:
        raise ValueError(f"Unknown environment: {env_type}")


def create_agent(agent_type: str, env):
    """Create agent for environment"""
    config = {'action_space': env.get_action_space()}

    if agent_type == 'random':
        # Create a generic random agent that can work with any environment
        return RandomAgent(config)
    elif agent_type == 'rule_based':
        return RuleBasedAgent(config)
    elif agent_type == 'q_learning':
        config.update({'alpha': 0.1, 'gamma': 0.9, 'epsilon': 0.1})
        return QLearningAgent(config)
    else:
        raise ValueError(f"Unknown agent: {agent_type}")


async def run_evaluation_demo():
    """Run complete evaluation demo"""
    logger.info("🚀 Mini RL Platform Demo")
    logger.info("=" * 50)

    # Initialize LLM and reward engine
    llm_providers = []
    llm_api_key = os.getenv("GROQ_API_KEY")
    if llm_api_key:
        logger.info("Using Groq provider via GROQ_API_KEY")
        llm_providers.append(GroqProvider(llm_api_key))
    else:
        logger.info("Using mock LLM provider (set GROQ_API_KEY for real LLM)")
        llm_providers.append(MockProvider())

    llm_manager = LLMManager(llm_providers)
    reward_engine = RewardEngine(llm_manager)

    # Initialize evaluator and leaderboard
    evaluator = EvaluationRunner(reward_engine)
    leaderboard = Leaderboard()

    # Define evaluation scenarios
    scenarios = [
        {
            'task_file': 'grid_world_basic.json',
            'agents': ['random', 'rule_based', 'q_learning'],
            'episodes': 5
        },
        {
            'task_file': 'text_decision_ethics.json',
            'agents': ['random', 'rule_based'],
            'episodes': 3
        }
    ]

    # Run evaluations
    for scenario in scenarios:
        logger.info(f"📋 Loading task: {scenario['task_file']}")
        task_config = await load_task_config(scenario['task_file'])
        env = create_environment_from_config(task_config)

        logger.info(f"🎯 Environment: {task_config['env_type']}")
        logger.info(f"📝 Description: {task_config['description']}")

        for agent_type in scenario['agents']:
            logger.info(f"🤖 Testing agent: {agent_type}")

            # Create agent
            agent = create_agent(agent_type, env)

            # Run episodes
            results = await evaluator.run_multiple_episodes(
                env, agent, scenario['episodes'], task_config['config'].get('max_steps', 100)
            )

            # Calculate metrics
            metrics = evaluator.calculate_metrics(results)

            # Update leaderboard
            agent_name = f"{agent_type}_{task_config['task_id']}"
            leaderboard.add_result(agent_name, task_config['env_type'], metrics)

            # Print results
            logger.info(f"  Avg Reward: {metrics['avg_total_reward']:.3f}")
            logger.info(f"  Success Rate: {metrics['success_rate']:.3f}")
            logger.info(f"  Avg Steps: {metrics['avg_steps']:.1f}")
            logger.info(f"  Episodes: {metrics['num_episodes']}")

    # Show final leaderboard
    logger.info("\n🏆 Final Leaderboard")
    logger.info("=" * 30)

    for env_type in ['grid_world', 'text_decision', 'code_logic']:
        rankings = leaderboard.get_rankings(env_type)
        if rankings:
            logger.info(f"{env_type.upper()}:")
            for i, (agent, score) in enumerate(rankings[:3], 1):
                logger.info(f"{i}. {agent}: {score:.3f}")

    logger.info("\n✅ Demo completed!")
    logger.info("To run the API server:")
    logger.info("python api/app.py")
    logger.info("To run with real LLM:")
    logger.info("GROQ_API_KEY=gsk_... python demo.py")


if __name__ == "__main__":
    asyncio.run(run_evaluation_demo())
