import React from "react";
import { SectionHead } from "../../components/common";

function Audit() { return <><SectionHead eyebrow="PERMANENT RECORD" title="감사 로그" desc="판정 근거와 법령 출처를 변경 불가능한 기록으로 보관합니다."/><div className="single-panel audit-table"><div className="table-head"><span>시간</span><span>사용자</span><span>행위</span><span>대상 / 근거</span><span>상태</span></div>{[["10:42:18","AI Vision","PPE 위반 판정","EVT-8821 · 모델 v2.4.1","기록 완료"],["10:38:02","박서진","조건부 승인","PTW-2026-0713-021 · 제241조","기록 완료"],["10:21:44","김현수","체크리스트 제출","PTW-2026-0713-018","기록 완료"],["09:58:11","AI 분석","SIMOPS 충돌 판정","PTW-2026-0713-024 · RULE-18","검토 필요"]].map(r=><div className="table-row" key={r[0]}>{r.map((x,i)=><span key={i}>{x}</span>)}</div>)}</div></>; }

export default Audit;
