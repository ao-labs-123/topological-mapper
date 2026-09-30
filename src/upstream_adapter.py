from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_stage_entry(stage_name: str, stage_value: Any) -> Dict[str, Any]:
    if stage_value is None:
        return {}
    if isinstance(stage_value, dict):
        normalized = dict(stage_value)
        if "stage" not in normalized and stage_name in {"stage3", "stage4", "stage5"}:
            normalized["stage"] = stage_name
        return normalized
    if isinstance(stage_value, (str, int, float, bool)):
        return {"result": stage_value}
    if isinstance(stage_value, list):
        return {"structure": stage_value}
    return {"value": stage_value}


def _normalize_upstream_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {}

    normalized = dict(record)
    for stage_name in ("stage3", "stage4", "stage5"):
        if stage_name in normalized:
            normalized[stage_name] = _normalize_stage_entry(stage_name, normalized[stage_name])
    return normalized


def normalize_upstream_payload(payload: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Accept several upstream payload shapes and convert them to GraphBuilder input.

    Supported forms include:
      - {"particles": [...], "records": [...]}
      - {"particle_data": [...], "log_data": [...]} 
      - {"data": {"particles": [...], "records": [...]}}
      - already-normalized (particle_data, log_data)
    """
    if isinstance(payload, tuple) and len(payload) == 2:
        particle_data, log_data = payload
        return list(particle_data or []), list(log_data or [])

    if not isinstance(payload, dict):
        raise TypeError("Upstream payload must be a dict or a (particle_data, log_data) tuple.")

    nested = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    particle_data = (
        payload.get("particle_data")
        or payload.get("particles")
        or nested.get("particle_data")
        or nested.get("particles")
        or []
    )
    log_data = (
        payload.get("log_data")
        or payload.get("records")
        or payload.get("log")
        or payload.get("events")
        or nested.get("log_data")
        or nested.get("records")
        or nested.get("log")
        or nested.get("events")
        or []
    )

    particle_data = [dict(item) for item in _as_list(particle_data) if isinstance(item, dict)]
    log_data = [_normalize_upstream_record(dict(item)) for item in _as_list(log_data) if isinstance(item, dict)]

    return particle_data, log_data


def build_graph_from_upstream_payload(payload: Any):
    from .graph import GraphBuilder

    particle_data, log_data = normalize_upstream_payload(payload)
    return GraphBuilder.build_graph(particle_data, log_data)


def load_upstream_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_upstream_repo(
    repo_dir: str | Path | None = None,
    *,
    particle_repo_dir: str | Path | None = None,
    log_repo_dir: str | Path | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if (
        repo_dir is not None
        and particle_repo_dir is not None
        and log_repo_dir is not None
        and Path(repo_dir) not in {Path(particle_repo_dir), Path(log_repo_dir)}
    ):
        raise ValueError("When passing repo_dir, it must match the particle_repo_dir or log_repo_dir, or be omitted.")

    if particle_repo_dir is not None or log_repo_dir is not None:
        particle_root = Path(particle_repo_dir or repo_dir or ".")
        log_root = Path(log_repo_dir or repo_dir or ".")
    else:
        repo_root = Path(repo_dir or ".")
        particle_root = repo_root
        log_root = repo_root

    particle_file = next(
        (
            path
            for path in (
                particle_root / "particles.json",
                particle_root / "data" / "particles.json",
            )
            if path.exists()
        ),
        None,
    )
    log_file = next(
        (
            path
            for path in (
                log_root / "data" / "log.json",
                log_root / "log.json",
            )
            if path.exists()
        ),
        None,
    )

    if particle_file is None and log_file is None:
        raise FileNotFoundError(
            f"Could not find either particles or log files under upstream repo(s): {particle_root}, {log_root}. "
            "Expected particles.json and data/log.json or log.json."
        )

    if particle_file is None:
        raise FileNotFoundError(
            f"Could not find particles.json in {particle_root}. "
            "Pass the particle-encapsulation repo as particle_repo_dir."
        )
    if log_file is None:
        raise FileNotFoundError(
            f"Could not find log.json in {log_root}. "
            "Pass the input-parser repo as log_repo_dir."
        )

    payload = {
        "particles": load_upstream_json(particle_file),
        "records": load_upstream_json(log_file),
    }
    return normalize_upstream_payload(payload)
