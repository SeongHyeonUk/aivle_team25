import React, { useState } from "react";
import { Activity, BarChart3, Camera, Check, Eye, EyeOff, Factory, FileSearch, HardHat, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import Feature from "../../components/common/Feature";

function Login({ onLogin, notify }) {
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState("worker");
  const [form, setForm] = useState({ id: "SS-24018", password: "safety2026" });
  const submit = (e) => { e.preventDefault(); if (!form.id || !form.password) return notify("사번과 비밀번호를 입력해 주세요."); onLogin({ role, name: role === "worker" ? "김현수" : "박서진" }); };
  return <main className="login-page">
    <section className="visual-panel">
      <header className="brand"><Factory size={34}/><span>SMART SHIPYARD</span><em>AI SAFETY</em></header>
      <div className="hero-copy"><span className="eyebrow">CONNECTED SAFETY PLATFORM</span><h1>AI 기반 스마트 조선소<br/><strong>안전관리 시스템</strong></h1><p>실시간 위험 감지부터 작업 허가, TBM까지.<br/>조선소의 모든 안전 데이터를 하나로 연결합니다.</p></div>
      <div className="scene"><div className="scan-grid"/><div className="pulse p1"/><div className="pulse p2"/><div className="float f1"><ShieldCheck/>PPE 감지 <b>정상</b></div><div className="float f2"><Camera/>CAM-12 <b>LIVE</b></div><div className="float f3"><Activity/>위험도 <b>낮음</b></div></div>
      <div className="feature-strip"><Feature icon={Camera} title="AI 영상 관제" text="24시간 보호구·위험구역 감지"/><Feature icon={FileSearch} title="스마트 허가서" text="충돌 분석과 승인조건 자동 도출"/><Feature icon={BarChart3} title="예측 안전관리" text="블록별 위험도를 미리 확인"/></div>
      <footer>© 2026 Smart Shipyard AI Safety Management System</footer>
    </section>
    <section className="login-wrap"><form className="login-card" onSubmit={submit}>
      <div className="login-head"><div className="shield-icon"><LockKeyhole/></div><div><span className="eyebrow">SECURE ACCESS</span><h2>안전관리 시스템 로그인</h2><p>허가된 임직원만 접속할 수 있습니다.</p></div></div>
      <label><span>사번</span><div className="input-box"><UserRound/><input value={form.id} onChange={e=>setForm({...form,id:e.target.value})} placeholder="사번을 입력하세요"/></div></label>
      <label><span>비밀번호</span><div className="input-box"><LockKeyhole/><input type={showPassword?"text":"password"} value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/><button type="button" className="icon-btn" onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff/>:<Eye/>}</button></div></label>
      <div className="role-label">가입 역할</div><div className="role-choice"><button type="button" className={role==="worker"?"active":""} onClick={()=>setRole("worker")}><HardHat/><span><b>현장 작업자</b><small>TBM · 체크리스트 · 신고</small></span>{role==="worker"&&<Check/>}</button><button type="button" className={role==="admin"?"active":""} onClick={()=>setRole("admin")}><ShieldCheck/><span><b>관리자</b><small>관제 · 허가서 · 위험예측</small></span>{role==="admin"&&<Check/>}</button></div>
      <button className="primary-btn" type="submit">시스템 접속 <span>→</span></button>
      <div className="login-note"><ShieldCheck/>JWT 보안 인증 · 역할 기반 접근 제어(RBAC)</div>
      <div className="demo-hint"><b>목업 계정</b><span>입력된 샘플 계정으로 바로 접속할 수 있습니다.</span></div>
    </form></section>
  </main>;
}

export default Login;
