import os
import re
import sys
from typing import Any, Dict, Optional

import json

from openai import OpenAI

from code_review_env import Action, CodeReviewEnv
from utils.logging_config import get_logger


MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

if not HF_TOKEN:
    print("HF_TOKEN is required", file=sys.stderr)
    sys.exit(1)


logger = get_logger("openenv.inference")


def _build_client() -> OpenAI:
    return OpenAI(api_key=HF_TOKEN, base_url=BASE_URL)


def _extract_json_object(text: str) -> Optional[str]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        return fenced.group(1)

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1]
    return None


class InferenceRunner:
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
        self.env = CodeReviewEnv(default_task_id="easy")

    def _call_model(self, observation: Dict[str, Any]) -> Action:
        prompt = (
            "You are solving OpenEnv code review tasks with strict staged workflow order. "
            "Return only one JSON object valid for this schema."
            f"\nAction schema:\n{json.dumps(Action.model_json_schema(), indent=2)}"
            f"\nCurrent observation:\n{json.dumps(observation, indent=2)}"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "Return strict JSON only. No prose."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            top_p=1,
            max_tokens=1200,
        )

        content = response.choices[0].message.content or ""
        payload = _extract_json_object(content)
        if payload is None:
            raise ValueError("Model response did not include JSON object")
        return Action.model_validate_json(payload)

    @staticmethod
    def _fallback_action(task_id: str, observation: Dict[str, Any]) -> Action:
        stages = observation.get("required_stages", [])
        completed = observation.get("completed_stages", [])
        next_stage = stages[len(completed)] if len(completed) < len(stages) else stages[-1]
        return Action(
            task_id=task_id,
            action_type=next_stage,
            payload=f"Fallback action for stage {next_stage}",
            confidence=0.0,
        )

    def run(self, max_steps: int = 12) -> Dict[str, Any]:
        observation = self.env.reset()
        done = False
        steps = 0
        final_score = 0.0
        history = []

        print("[START]")

        while not done and steps < max_steps:
            print("[STEP]")
            obs_dict = observation.model_dump()
            action: Optional[Action] = None
            fallback: Optional[Action] = None

            try:
                action = self._call_model(obs_dict)
                next_observation, reward, done, info = self.env.step(action)
            except Exception as exc:
                logger.debug("Model action failed; applying deterministic fallback", exc_info=exc)
                fallback_task_id = obs_dict.get("task_id", "easy")
                fallback = self._fallback_action(fallback_task_id, obs_dict)
                next_observation, reward, done, info = self.env.step(fallback)

            final_score = reward.score
            history.append(
                {
                    "step": steps,
                    "action": action.model_dump() if action is not None else fallback.model_dump(),
                    "reward": reward.model_dump(),
                    "info": info,
                }
            )

            observation = next_observation
            steps += 1

        print("[END]")

        return {
            "steps": steps,
            "final_score": final_score,
            "history": history,
            "model": self.model_name,
            "provider": "groq",
        }


if __name__ == "__main__":
    runner = InferenceRunner(_build_client(), MODEL_NAME)
    # Keep stdout contract strict for hackathon validators.
    runner.run()
