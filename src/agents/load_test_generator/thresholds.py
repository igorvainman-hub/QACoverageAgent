from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import EffectiveThresholds, ThresholdConfig, ThresholdValues

DEFAULT_THRESHOLDS = ThresholdValues(p95=500, p99=1000, error_rate=0.01)


def load_threshold_config(path: Path | None) -> EffectiveThresholds | ThresholdConfig:
    """Load user thresholds, or return the explicitly marked placeholder default."""
    if path is None:
        return EffectiveThresholds(values=DEFAULT_THRESHOLDS, sources=["default placeholder"], is_placeholder=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return ThresholdConfig.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"Invalid k6 thresholds file {path}: {error}") from error


def thresholds_for_tags(config: ThresholdConfig | EffectiveThresholds, tags: list[str]) -> EffectiveThresholds:
    """Use the strictest matching tag threshold, otherwise the configured default."""
    if isinstance(config, EffectiveThresholds):
        return config
    matched = [(tag, config.by_tag[tag]) for tag in dict.fromkeys(tags) if tag in config.by_tag]
    if not matched:
        return EffectiveThresholds(values=config.default, sources=["default"])
    return EffectiveThresholds(
        values=ThresholdValues(
            p95=min(value.p95 for _, value in matched),
            p99=min(value.p99 for _, value in matched),
            error_rate=min(value.error_rate for _, value in matched),
        ),
        sources=[tag for tag, _ in matched],
    )
