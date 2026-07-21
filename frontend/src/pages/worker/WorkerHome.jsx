import React, { useEffect, useMemo, useState } from "react";
import { Activity, ClipboardCheck, Clock3, Map, Send, ShieldCheck, Siren, Users } from "lucide-react";
import { apiRequest } from "../../api/client";
import { Panel, Stat, Task } from "../../components/common";

const statusLabel = {
  draft: "작성 중",
  pending_review: "검토 대기",
  approved: "승인 완료",
  conditionally_approved: "조건부 승인",
};

const formatTime = value => value
  ? new Date(value).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false })
  : "시간 미정";

const conditionsText = value => {
  if (!value) return "관리자가 등록한 허가서의 승인 조건을 확인해 주세요.";
  try {
    const parsed = typeof value === "string" ? JSON.parse(value) : value;
    return Array.isArray(parsed) && parsed.length ? parsed.join(" · ") : String(value);
  } catch {
    return String(value);
  }
};

function WorkerHome({ notify, session }) {
  const [permit, setPermit] = useState(null);
  const [loading, setLoading] = useState(true);
  const authorization = useMemo(() => ({ Authorization: `Bearer ${session.token}` }), [session.token]);

  useEffect(() => {
    apiRequest("/api/work-permits/today", { headers: authorization })
      .then(data => setPermit(data?.id ? data : null))
      .catch(error => notify(error.message))
      .finally(() => setLoading(false));
  }, [authorization]);

  const today = new Intl.DateTimeFormat("ko-KR", { dateStyle: "full" }).format(new Date());
  const workTime = permit ? `${formatTime(permit.start_time)} - ${formatTime(permit.end_time)}` : "등록된 작업 없음";
  const workLocation = permit?.block_code || permit?.site_name || "작업 위치 미정";
  const permitStatus = permit ? (statusLabel[permit.status] || permit.status) : "허가서 없음";

  return <>
    <div className="welcome"><div><span className="eyebrow">{today}</span><h2>{session.name} 님, 오늘도 안전하게 👋</h2><p>작업 시작 전 TBM과 승인 조건을 꼭 확인해 주세요.</p></div><div className="weather"><span>현장 기상</span><b>24°C · 맑음</b><small>풍속 3.2m/s · 작업 적합</small></div></div>
    <div className="stat-grid worker"><Stat icon={Clock3} label="오늘 작업" value={workTime} sub={permit ? `${workLocation} · ${permit.work_type || "작업 유형 미정"}` : "관리자가 허가서를 등록하면 표시됩니다."}/><Stat icon={ShieldCheck} label="작업 허가" value={permitStatus} sub={permit?.permit_no || "-"} tone="cyan"/><Stat icon={ClipboardCheck} label="필수 조치" value={permit ? "확인 필요" : "-"} sub={permit ? "허가 조건을 확인해 주세요." : "등록된 항목 없음"} tone="orange"/><Stat icon={Activity} label="현장 위험도" value={permit?.is_high_risk ? "높음" : "낮음"} sub={permit ? "허가서 기준" : "작업 정보 없음"} tone="green"/></div>
    <div className="two-col"><Panel title="오늘의 작업 허가" action={permit?.permit_no || "실시간 연동"}>
      {loading ? <div className="permit-empty">오늘의 작업을 불러오는 중입니다.</div> : permit ? <div className="permit-card"><div className="permit-top"><span className={`badge ${permit.status === "approved" ? "cyan" : "orange"}`}>{permitStatus}</span><small>{permit.permit_no}</small></div><h3>{permit.work_title || "작업명 미입력"}</h3><div className="permit-meta"><span><Clock3/>{workTime}</span><span><Users/>{permit.work_type || "작업 유형 미정"} · {permit.worker_count || 0}명</span><span><Map/>{workLocation}</span></div><div className="condition"><ShieldCheck/><div><b>핵심 승인 조건</b><p>{conditionsText(permit.recommended_conditions)}</p></div></div></div> : <div className="permit-empty large">오늘 등록된 작업허가서가 없습니다.</div>}
    </Panel><Panel title="작업 전 확인" action="4개 항목"><Task done text="TBM 브리핑 참여" time="완료"/><Task done text="개인 보호구 점검" time="완료"/><Task done={Boolean(permit)} text="작업 허가 조건 확인" time={permit ? "허가서 연동 완료" : "허가서 대기 중"}/><Task text="현장 도착 확인" time="작업 위치에서 확인" onClick={() => notify("현장 도착이 확인되었습니다.")}/></Panel></div>
    <div className="emergency" onClick={() => notify("긴급 신고 화면으로 연결됩니다.")}><Siren/><div><b>현장에서 위험을 발견하셨나요?</b><span>사진이나 음성으로 즉시 신고하세요.</span></div><button>위험 신고하기 <Send/></button></div>
  </>;
}

export default WorkerHome;
