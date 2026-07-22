"""작업허가서(PTW) 입출력 스키마 — 명세 §5.

이 모듈은 다른 모든 컴포넌트의 계약이다. 룰엔진·생성기·API가 모두 여기에 의존한다.

설계 의도 하나만 강조한다: 명세 §11의 "자동 승인 로직 작성 금지"를 주석이나
관례가 아니라 **타입으로** 강제한다. `PermitDecision.verdict_source`는
Literal["rule_engine"]이고 `human_decision_required`는 Literal[True]라서,
LLM이 판정을 뒤집거나 시스템이 사람 개입을 건너뛰는 객체는 애초에 만들 수 없다.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --------------------------------------------------------------------------
# Enum — 도메인 용어
# --------------------------------------------------------------------------

class WorkType(str, Enum):
    """작업 종류.

    TODO(팀확인): 명세 §5.1의 enum 목록을 그대로 옮겼다. 조선소 현장 용어
    기준으로 최종 확정 필요(선급 검사 등 누락 항목 여부).
    """

    화기작업 = "화기작업"
    도장 = "도장"
    사상 = "사상"
    양중 = "양중"
    밀폐공간작업 = "밀폐공간작업"
    일반 = "일반"
    취부 = "취부"
    용접 = "용접"


class AreaType(str, Enum):
    """작업 구역 유형."""

    블록내부 = "블록내부"
    도크 = "도크"
    탱크 = "탱크"
    개방구역 = "개방구역"


class Verdict(str, Enum):
    """판정 라벨. 룰엔진만 이 값을 결정한다 (명세 §2)."""

    승인제안 = "승인제안"
    조건부승인 = "조건부승인"
    반려 = "반려"


class Severity(str, Enum):
    """위반 심각도. hard 1건이면 무조건 반려 (명세 §2)."""

    hard = "hard"
    conditional = "conditional"


class RiskCategory(str, Enum):
    """위험 카테고리. 합성 데이터 커버리지 보장용 (명세 §8)."""

    인적 = "인적"
    화재폭발 = "화재폭발"
    질식중독 = "질식중독"
    혼재 = "혼재"


class SpatialRelation(str, Enum):
    """두 허가서 구역 간의 공간 관계. simops.yaml의 `spatial` 값과 대응."""

    동일구역 = "동일구역"
    인접구역 = "인접구역"
    원거리 = "원거리"


# --------------------------------------------------------------------------
# 입력 — 작업허가서 (명세 §5.1)
# --------------------------------------------------------------------------

class Zone(BaseModel):
    """작업 구역. coordinates는 ①디지털 트윈 모듈 연동용 2.5D 좌표."""

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1, description="블록/도크/탱크 식별자 (예: B-12)")
    area_type: AreaType
    coordinates: tuple[float, float] | None = None


class TimeWindow(BaseModel):
    """작업 시간 창. 룰엔진의 시간 중첩 판정 대상."""

    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _end_after_start(self) -> TimeWindow:
        if self.end <= self.start:
            raise ValueError("time_window.end는 start보다 뒤여야 한다")
        return self

    def overlaps(self, other: TimeWindow) -> bool:
        """반개구간 [start, end) 기준 중첩 판정.

        경계가 맞닿는 경우(A가 12:00에 끝나고 B가 12:00에 시작)는 중첩이
        아니다. 같은 순간에 두 작업이 동시에 존재하지는 않기 때문이다.
        """
        return self.start < other.end and other.start < self.end


class SpecialConditions(BaseModel):
    """특수 조건. 하드 제약 판정의 핵심 입력."""

    model_config = ConfigDict(extra="forbid")

    gas_measured: bool = False       # 밀폐공간 가스 측정 여부
    ventilation: bool = False        # 환기 여부
    adjacent_flammable: bool = False  # 인접 인화물 존재
    # 산업안전보건기준에 관한 규칙 제241조의2가 요구하는 화재감시자 지정·배치.
    # 명세 §5.1 예시에는 없는 필드지만, 이것 없이는 COND-005가 "인화물이 있으면
    # 항상 발화"하는 무조건 규칙이 되어 오탐만 늘린다. 기본값을 False(미배치)로
    # 두는 것은 나머지 필드와 같은 원칙이다 — 안전 조치는 신고된 경우에만 인정한다.
    fire_watch_assigned: bool = False  # 화재감시자 배치 여부


class PermitRequest(BaseModel):
    """작업허가서 1건. KOSHA P-94 / OSHA 1915 공개 표준 기반.

    명세 §11: 실제 조선소 허가서 양식·데이터는 사용하지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    permit_id: str = Field(min_length=1)
    work_type: WorkType
    zone: Zone
    time_window: TimeWindow
    worker_count: int = Field(ge=1)
    supervisor_present: bool = False
    declared_ppe: list[str] = Field(default_factory=list)
    work_description: str = ""
    special_conditions: SpecialConditions = Field(default_factory=SpecialConditions)


# --------------------------------------------------------------------------
# 출력 — 판정 결과 (명세 §5.2)
# --------------------------------------------------------------------------

class Violation(BaseModel):
    """룰엔진이 포착한 위반 1건."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: Severity
    summary: str
    legal_basis: str | None = None
    conflicting_permit: str | None = Field(
        default=None, description="SIMOPS 위반일 때 충돌 상대 허가서 ID"
    )
    risk_category: RiskCategory | None = None


class SimilarCase(BaseModel):
    """유사 사고사례. 4단계 Retrieval이 채운다."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    score: float


class PermitDecision(BaseModel):
    """최종 판정 결과.

    `verdict`는 룰엔진이 결정하고, `reject_comment`/`recommended_actions`는
    5단계에서 LLM이 채운다. MVP에서는 None/빈 리스트로 남는다.
    """

    model_config = ConfigDict(extra="forbid")

    permit_id: str
    verdict: Verdict

    # 아래 두 필드는 값을 바꿀 수 없다 — 명세 §2·§11을 타입으로 고정한 것이다.
    verdict_source: Literal["rule_engine"] = "rule_engine"
    human_decision_required: Literal[True] = True

    violations: list[Violation] = Field(default_factory=list)

    # LLM 생성 필드 (5단계). MVP에서는 채우지 않는다.
    reject_comment: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)

    # Retrieval 결과 (4단계). MVP에서는 비어 있다.
    similar_cases: list[SimilarCase] = Field(default_factory=list)

    @property
    def hard_violations(self) -> list[Violation]:
        return [v for v in self.violations if v.severity is Severity.hard]
