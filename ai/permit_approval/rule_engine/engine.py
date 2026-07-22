"""규칙 평가 — 명세 §6.1.

이 모듈의 계약은 딱 하나다: **위반 목록만 반환한다.**
verdict 종합(승인제안/조건부승인/반려)은 orchestrator.py의 몫이다.
이 경계를 흐리면 명세 §2의 "판정 주체는 룰엔진" 보장이 무너진다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from config_loader import load_config, resolve
from rule_engine.conflict_matrix import AdjacencyResolver, GridConflictMatrix
from schemas.permit import (
    PermitRequest,
    RiskCategory,
    Severity,
    SpatialRelation,
    Violation,
    WorkType,
)

_SUPPORTED_TEMPORAL = {"시간중첩"}


def _load_rules(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        rules = yaml.safe_load(f) or []
    if not isinstance(rules, list):
        raise ValueError(f"{path.name}: 최상위는 규칙 리스트여야 한다")
    for rule in rules:
        if "rule_id" not in rule:
            raise ValueError(f"{path.name}: rule_id가 없는 규칙이 있다 -> {rule}")
    return rules


def _as_severity(rule: dict[str, Any]) -> Severity:
    return Severity(rule.get("severity", "conditional"))


def _as_risk_category(rule: dict[str, Any]) -> RiskCategory | None:
    raw = rule.get("risk_category")
    return RiskCategory(raw) if raw else None


class RuleEngine:
    """YAML 규칙을 읽어 허가서를 평가한다."""

    def __init__(
        self,
        hard_rules: list[dict[str, Any]],
        simops_rules: list[dict[str, Any]],
        adjacency: AdjacencyResolver,
    ) -> None:
        self.hard_rules = hard_rules
        self.simops_rules = simops_rules
        self.adjacency = adjacency
        self._validate_rules()

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> RuleEngine:
        config = config or load_config()
        rules_dir = resolve(config["paths"]["rules_dir"])
        return cls(
            hard_rules=_load_rules(rules_dir / "hard_constraints.yaml"),
            simops_rules=_load_rules(rules_dir / "simops.yaml"),
            adjacency=GridConflictMatrix.from_config(config),
        )

    def _validate_rules(self) -> None:
        """YAML 오타를 조용히 삼키지 않는다.

        규칙 파일은 팀원이 직접 편집하는 파일이다. work_type에 오타가 나면
        그 규칙은 영원히 발화하지 않는데, 안전 시스템에서 조용히 꺼진 규칙은
        가장 위험한 실패 모드다. 로드 시점에 터뜨린다.
        """
        seen: set[str] = set()
        for rule in [*self.hard_rules, *self.simops_rules]:
            rid = rule["rule_id"]
            if rid in seen:
                raise ValueError(f"중복된 rule_id: {rid}")
            seen.add(rid)

            cond = rule.get("condition", {})
            for key in ("work_type", "conflict_with"):
                for value in cond.get(key, []) or []:
                    WorkType(value)  # 미정의 값이면 ValueError
            for value in cond.get("spatial", []) or []:
                SpatialRelation(value)
            temporal = cond.get("temporal")
            if temporal is not None and temporal not in _SUPPORTED_TEMPORAL:
                raise ValueError(
                    f"{rid}: 지원하지 않는 temporal 값 '{temporal}' "
                    f"(지원: {sorted(_SUPPORTED_TEMPORAL)})"
                )
            _as_severity(rule)
            _as_risk_category(rule)

    # ---------------------------------------------------------------- 단일 규칙

    def _match_single(self, permit: PermitRequest, cond: dict[str, Any]) -> bool:
        """hard_constraints.yaml의 condition을 허가서 1건에 대해 평가."""
        work_types = cond.get("work_type")
        if work_types and permit.work_type.value not in work_types:
            return False

        area_types = cond.get("area_type")
        if area_types and permit.zone.area_type.value not in area_types:
            return False

        for field, expected in (cond.get("special_conditions") or {}).items():
            if not hasattr(permit.special_conditions, field):
                raise ValueError(f"special_conditions에 없는 필드: {field}")
            if getattr(permit.special_conditions, field) != expected:
                return False

        if "supervisor_present" in cond:
            if permit.supervisor_present != cond["supervisor_present"]:
                return False

        missing_ppe = cond.get("missing_ppe")
        if missing_ppe:
            declared = set(permit.declared_ppe)
            if all(item in declared for item in missing_ppe):
                return False  # 전부 갖췄으면 위반 아님

        threshold = cond.get("worker_count_gte")
        if threshold is not None and permit.worker_count < threshold:
            return False

        # condition이 비어 있으면 모든 허가서에 매치된다. 그런 규칙은 사고다.
        if not cond:
            return False

        return True

    def evaluate_hard_constraints(self, permit: PermitRequest) -> list[Violation]:
        """진행 중 허가서와 무관하게 허가서 자체만 보고 판정."""
        violations = []
        for rule in self.hard_rules:
            if self._match_single(permit, rule.get("condition", {})):
                violations.append(
                    Violation(
                        rule_id=rule["rule_id"],
                        severity=_as_severity(rule),
                        summary=rule.get("summary", rule.get("name", "")),
                        legal_basis=rule.get("legal_ref"),
                        risk_category=_as_risk_category(rule),
                    )
                )
        return violations

    # ---------------------------------------------------------------- SIMOPS

    def _match_pair(
        self,
        new: PermitRequest,
        active: PermitRequest,
        rule: dict[str, Any],
    ) -> bool:
        cond = rule.get("condition", {})

        if cond.get("temporal") == "시간중첩":
            if not new.time_window.overlaps(active.time_window):
                return False

        allowed_spatial = cond.get("spatial")
        if allowed_spatial:
            relation = self.adjacency.relation(new.zone.block_id, active.zone.block_id)
            if relation.value not in allowed_spatial:
                return False

        lhs = cond.get("work_type") or []
        rhs = cond.get("conflict_with") or []
        forward = new.work_type.value in lhs and active.work_type.value in rhs
        if forward:
            return True
        if rule.get("bidirectional", True):
            return new.work_type.value in rhs and active.work_type.value in lhs
        return False

    def evaluate_simops(
        self,
        permit: PermitRequest,
        active_permits: Sequence[PermitRequest],
    ) -> list[Violation]:
        """신규 허가서를 진행 중 허가서 목록과 대조."""
        violations = []
        for active in active_permits:
            if active.permit_id == permit.permit_id:
                continue  # 자기 자신과는 충돌하지 않는다
            for rule in self.simops_rules:
                if self._match_pair(permit, active, rule):
                    violations.append(
                        Violation(
                            rule_id=rule["rule_id"],
                            severity=_as_severity(rule),
                            summary=rule.get("summary", rule.get("name", "")),
                            legal_basis=rule.get("legal_ref"),
                            conflicting_permit=active.permit_id,
                            risk_category=_as_risk_category(rule),
                        )
                    )
        return violations

    # ---------------------------------------------------------------- 진입점

    def evaluate(
        self,
        permit: PermitRequest,
        active_permits: Iterable[PermitRequest] = (),
    ) -> list[Violation]:
        """위반 목록을 반환한다. verdict는 계산하지 않는다 (명세 §6.1)."""
        active = list(active_permits)
        return [
            *self.evaluate_hard_constraints(permit),
            *self.evaluate_simops(permit, active),
        ]
