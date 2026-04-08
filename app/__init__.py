"""OpenEnv code review package."""

from .env import CodeReviewOpenEnv
from .models import Action, Observation, Reward

__all__ = ["CodeReviewOpenEnv", "Action", "Observation", "Reward", "app"]


def __getattr__(name: str):
    if name == "app":
        from api.app import app as fastapi_app

        return fastapi_app
    raise AttributeError(f"module 'app' has no attribute {name!r}")
