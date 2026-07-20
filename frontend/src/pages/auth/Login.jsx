import React, { useState } from "react";
import { Activity, BarChart3, Camera, Check, Eye, EyeOff, Factory, FileSearch, HardHat, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import Feature from "../../components/common/Feature";
import { apiRequest } from "../../api/client";

function Login({ initialUsername, onLogin, onRegister, notify }) {
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ username: initialUsername || "", password: "" });
  const submit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.password) return notify("아이디와 비밀번호를 입력해 주세요.");
    setSubmitting(true);
    try {
      const result = await apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify(form) });
      const roles = result.user.roles || [];
      const isSupervisor = roles.includes("ADMIN") || roles.includes("SAFETY_MANAGER");
      onLogin({ token: result.accessToken, role: isSupervisor ? "admin" : "worker", roles, name: result.user.name, username: result.user.username });
    } catch (error) { notify(error.message); } finally { setSubmitting(false); }
  };
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
      <label><span>아이디</span><div className="input-box"><UserRound/><input autoComplete="username" value={form.username} onChange={e=>setForm({...form,username:e.target.value})} placeholder="아이디를 입력하세요"/></div></label>
      <label><span>비밀번호</span><div className="input-box"><LockKeyhole/><input type={showPassword?"text":"password"} value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="비밀번호를 입력하세요"/><button type="button" className="icon-btn" onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff/>:<Eye/>}</button></div></label>
      <div className="auth-actions"><button type="button" className="secondary-auth-btn" onClick={onRegister}>회원가입</button><button className="primary-btn" type="submit" disabled={submitting}>{submitting?"접속 중...":"시스템 접속 →"}</button></div>
      <div className="login-note"><ShieldCheck/>Spring Security · 역할 기반 접근 제어(RBAC)</div>
    </form></section>
  </main>;
}

export default Login;
