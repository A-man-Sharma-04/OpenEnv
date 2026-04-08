"""
FastAPI Application for Mini RL Platform
"""
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Ensure repo root is on sys.path when running this module directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import our modules
from environments.grid_world import GridWorldEnv
from environments.text_decision import TextDecisionEnv
from environments.code_logic import CodeLogicEnv
from agents.base import RandomAgent, RuleBasedAgent, QLearningAgent
from evaluation.runner import EvaluationRunner, Leaderboard
from llm.provider import GroqProvider, LLMManager, MockProvider
from rewards.engine import RewardEngine
from utils.logging_config import get_logger


app = FastAPI(
    title="Mini RL Platform API",
    description="REST API for running reinforcement learning evaluations",
    version="1.0.0"
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Global state (in production, use proper database)
running_evaluations = {}
leaderboard = Leaderboard()

logger = get_logger("openenv.api")


def build_llm_manager() -> LLMManager:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        logger.info("Using Groq provider for backend LLM operations")
        try:
            providers = [GroqProvider(groq_api_key)]
        except ImportError as exc:
            logger.warning("Groq SDK unavailable in active interpreter; falling back to MockProvider: %s", exc)
            providers = [MockProvider()]
    else:
        logger.warning("GROQ_API_KEY is not set; using MockProvider")
        providers = [MockProvider()]
    return LLMManager(providers)


llm_manager = build_llm_manager()
reward_engine = RewardEngine(llm_manager)


# Pydantic models for API
class TaskConfig(BaseModel):
    env_type: str  # 'grid_world', 'text_decision', 'code_logic'
    config: Dict[str, Any]
    task_id: Optional[str] = None

class AgentConfig(BaseModel):
    agent_type: str  # 'random', 'rule_based', 'q_learning'
    config: Dict[str, Any]

class EvaluationRequest(BaseModel):
    task: TaskConfig
    agent: AgentConfig
    num_episodes: int = 10
    max_steps: int = 100

class EvaluationStatus(BaseModel):
    evaluation_id: str
    status: str  # 'running', 'completed', 'failed'
    progress: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class LeaderboardResponse(BaseModel):
    rankings: List[Dict[str, Any]]
    last_updated: datetime


# Environment factory
def create_environment(task_config: TaskConfig):
    """Create environment from config"""
    env_type = task_config.env_type
    config = task_config.config

    if env_type == 'grid_world':
        return GridWorldEnv(config)
    elif env_type == 'text_decision':
        return TextDecisionEnv(config)
    elif env_type == 'code_logic':
        return CodeLogicEnv(config)
    else:
        raise ValueError(f"Unknown environment type: {env_type}")

# Agent factory
def create_agent(agent_config: AgentConfig, env):
    """Create agent from config"""
    agent_type = agent_config.agent_type
    config = dict(agent_config.config)

    # Add action space info to config
    config['action_space'] = env.get_action_space()

    if agent_type == 'random':
        return RandomAgent(config)
    elif agent_type == 'rule_based':
        return RuleBasedAgent(config)
    elif agent_type == 'q_learning':
        return QLearningAgent(config)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


@app.post("/task/create", response_model=Dict[str, Any])
async def create_task(task: TaskConfig):
    """Create and validate a task"""
    try:
        env = create_environment(task)
        return {
            "task_id": task.task_id or str(uuid.uuid4()),
            "env_type": task.env_type,
            "action_space": env.get_action_space(),
            "observation_space": env.get_observation_space(),
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/evaluate", response_model=Dict[str, str])
async def start_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """Start an evaluation run"""
    evaluation_id = str(uuid.uuid4())

    # Store initial status
    running_evaluations[evaluation_id] = EvaluationStatus(
        evaluation_id=evaluation_id,
        status="running",
        progress=0.0
    )

    # Start background task
    background_tasks.add_task(run_evaluation_async, evaluation_id, request)

    return {"evaluation_id": evaluation_id, "status": "started"}


async def run_evaluation_async(evaluation_id: str, request: EvaluationRequest):
    """Run evaluation in background"""
    try:
        # Create environment and agent
        env = create_environment(request.task)
        agent = create_agent(request.agent, env)

        # Create evaluator
        evaluator = EvaluationRunner(reward_engine)

        # Run episodes
        results = await evaluator.run_multiple_episodes(
            env, agent, request.num_episodes, request.max_steps
        )

        # Calculate metrics
        metrics = evaluator.calculate_metrics(results)

        # Update leaderboard
        agent_name = f"{request.agent.agent_type}_{evaluation_id[:8]}"
        env_name = request.task.env_type
        leaderboard.add_result(agent_name, env_name, metrics)

        # Store results
        running_evaluations[evaluation_id] = EvaluationStatus(
            evaluation_id=evaluation_id,
            status="completed",
            progress=1.0,
            results={
                "metrics": metrics,
                "num_episodes": len(results),
                "agent_type": request.agent.agent_type,
                "env_type": request.task.env_type
            }
        )

    except Exception as e:
        running_evaluations[evaluation_id] = EvaluationStatus(
            evaluation_id=evaluation_id,
            status="failed",
            error=str(e)
        )


@app.get("/evaluate/{evaluation_id}", response_model=EvaluationStatus)
async def get_evaluation_status(evaluation_id: str):
    """Get evaluation status"""
    if evaluation_id not in running_evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return running_evaluations[evaluation_id]


@app.get("/leaderboard/{env_type}", response_model=LeaderboardResponse)
async def get_leaderboard(env_type: str):
    """Get leaderboard for environment type"""
    rankings = leaderboard.get_rankings(env_type)

    return LeaderboardResponse(
        rankings=[{"agent": agent, "score": score} for agent, score in rankings],
        last_updated=datetime.now()
    )


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_stats": llm_manager.get_stats(),
        "active_evaluations": len([e for e in running_evaluations.values() if e.status == "running"])
    }


@app.delete("/evaluate/{evaluation_id}")
async def cancel_evaluation(evaluation_id: str):
    """Cancel running evaluation"""
    if evaluation_id not in running_evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    status = running_evaluations[evaluation_id]
    if status.status == "running":
        status.status = "cancelled"
        return {"message": "Evaluation cancelled"}
    else:
        raise HTTPException(status_code=400, detail="Evaluation not running")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)