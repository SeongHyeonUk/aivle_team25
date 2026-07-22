"""config.yaml 로더.

명세 §11: 경로·모델명·top-k는 하드코딩하지 않는다. 모든 컴포넌트가
이 모듈을 통해 설정을 읽고, 상대 경로는 패키지 루트 기준으로 해석한다.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent


@functools.lru_cache(maxsize=None)
def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """config.yaml을 읽어 dict로 반환한다. 같은 경로는 캐시된다."""
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(relative: str | Path) -> Path:
    """config에 적힌 상대 경로를 패키지 루트 기준 절대 경로로 바꾼다."""
    p = Path(relative)
    return p if p.is_absolute() else ROOT / p
