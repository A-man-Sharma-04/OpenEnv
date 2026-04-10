from __future__ import annotations

from dataclasses import dataclass

from env.config import RewardConfig


@dataclass
class RewardBreakdown:
    base: float
    progress: float
    confidence: float
    invalid_penalty: float
    loop_penalty: float
    destructive_penalty: float


def compose_reward(score: float, completed_new_stage: bool, confidence: float, invalid: bool, looping: bool, destructive: bool) -> RewardBreakdown:
    cfg = RewardConfig()
    base = min(cfg.max_reward, max(0.0, score * cfg.stage_weight))
    progress = cfg.progress_bonus if completed_new_stage else 0.0
    confidence_midpoint = 1.0 - abs(0.75 - confidence)
    confidence_bonus = min(cfg.confidence_bonus_cap, max(0.0, confidence_midpoint * cfg.confidence_bonus_cap))
    return RewardBreakdown(
        base=base,
        progress=progress,
        confidence=confidence_bonus,
        invalid_penalty=cfg.invalid_action_penalty if invalid else 0.0,
        loop_penalty=cfg.loop_penalty if looping else 0.0,
        destructive_penalty=cfg.destructive_penalty if destructive else 0.0,
    )


def finalize_reward(breakdown: RewardBreakdown) -> float:
    cfg = RewardConfig()
    total = (
        breakdown.base
        + breakdown.progress
        + breakdown.confidence
        - breakdown.invalid_penalty
        - breakdown.loop_penalty
        - breakdown.destructive_penalty
    )
    return min(cfg.max_reward, max(0.0, total))
