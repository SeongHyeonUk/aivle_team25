import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, AlertTriangle, ArrowLeft, BarChart3, Bell, Building2, Camera,
  Check, CheckCircle2, ChevronDown, ClipboardCheck, Clock3, Eye, EyeOff,
  Factory, FileSearch, FileText, HardHat, Headphones, Languages, LayoutDashboard,
  LockKeyhole, LogOut, Map, Menu, Mic, Play, Plus, Radio, Search, Send,
  Settings, ShieldCheck, Siren, Sparkles, UploadCloud, UserRound, Users, X,
} from "lucide-react";
import "./styles.css";

const workerNav = [
  ["dashboard", "오늘의 작업", LayoutDashboard], ["tbm", "TBM 브리핑", Mic],
  ["checklist", "조치 체크리스트", ClipboardCheck], ["report", "위험 신고", Siren],
];
const adminNav = [
  ["dashboard", "통합 관제", LayoutDashboard], ["monitoring", "영상 감시", Camera],
  ["permits", "허가서 분석", FileSearch], ["risk", "위험 예측", BarChart3],
  ["standards", "기준 정보", Settings], ["audit", "감사 로그", FileText],
];

const incidents = [
  { time: "10:42", level: "긴급", title: "B-07 블록 안전벨트 미착용", meta: "CAM-12 · 조립 2팀", color: "red" },
  { time: "10:36", level: "주의", title: "C-03 블록 위험구역 접근", meta: "CAM-08 · 배관 1팀", color: "orange" },
  { time: "10:21", level: "확인", title: "A-12 블록 보호구 확인 완료", meta: "CAM-03 · 용접 4팀", color: "cyan" },
];

function App() {
  const [session, setSession] = useState(null);
  const [toast, setToast] = useState("");
  const notify = (message) => { setToast(message); window.clearTimeout(window.__toast); window.__toast = window.setTimeout(() => setToast(""), 2600); };
  return <>{session ? <Dashboard session={session} onLogout={() => setSession(null)} notify={notify} /> : <Login onLogin={setSession} notify={notify} />}{toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}</>;
}

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

function Feature({icon:Icon,title,text}) { return <article><Icon/><div><b>{title}</b><span>{text}</span></div></article>; }

function Dashboard({ session, onLogout, notify }) {
  const [page, setPage] = useState("dashboard"); const [mobile, setMobile] = useState(false);
  const nav = session.role === "worker" ? workerNav : adminNav;
  const title = nav.find(n=>n[0]===page)?.[1] || "대시보드";
  return <div className="app-shell">
    <aside className={mobile?"sidebar open":"sidebar"}><div className="side-brand"><Factory/><div><b>SMART SHIPYARD</b><span>AI SAFETY PLATFORM</span></div><button onClick={()=>setMobile(false)}><X/></button></div><div className="site-select"><Building2/><div><span>현재 사업장</span><b>거제 스마트 조선소</b></div><ChevronDown/></div><nav>{nav.map(([id,label,Icon])=><button key={id} className={page===id?"active":""} onClick={()=>{setPage(id);setMobile(false)}}><Icon/>{label}{id==="monitoring"&&<i>3</i>}</button>)}</nav><div className="side-bottom"><div className="user-chip"><div>{session.name[0]}</div><span><b>{session.name}</b><small>{session.role==="worker"?"현장 작업자 · 조립 2팀":"안전관리자 · 안전환경팀"}</small></span></div><button className="logout" onClick={onLogout}><LogOut/>로그아웃</button></div></aside>
    <main className="workspace"><header className="topbar"><button className="menu-btn" onClick={()=>setMobile(true)}><Menu/></button><div><span>거제 스마트 조선소 / {session.role==="worker"?"현장 작업자":"관리자"}</span><h1>{title}</h1></div><div className="top-actions"><div className="live"><i/> 시스템 정상</div><button><Bell/><i>3</i></button><div className="avatar">{session.name[0]}</div></div></header>
      <section className="content"><Page page={page} role={session.role} notify={notify}/></section>
    </main>
  </div>;
}

function Page({page,role,notify}) {
  if (role === "worker") return page==="tbm"?<TBM notify={notify}/>:page==="checklist"?<Checklist notify={notify}/>:page==="report"?<Report notify={notify}/>:<WorkerHome notify={notify}/>;
  return page==="monitoring"?<Monitoring notify={notify}/>:page==="permits"?<Permits notify={notify}/>:page==="risk"?<Risk/>:page==="standards"?<Standards notify={notify}/>:page==="audit"?<Audit/>:<AdminHome/>;
}

function WorkerHome({notify}) { return <><div className="welcome"><div><span className="eyebrow">2026년 7월 13일 월요일</span><h2>김현수 님, 오늘도 안전하게 👋</h2><p>작업 시작 전 TBM과 승인 조건을 꼭 확인해 주세요.</p></div><div className="weather"><span>현장 기상</span><b>24°C · 맑음</b><small>풍속 3.2m/s · 작업 적합</small></div></div><div className="stat-grid worker"><Stat icon={Clock3} label="오늘 작업" value="08:00 - 17:00" sub="B-07 블록 · 조립"/><Stat icon={ShieldCheck} label="작업 허가" value="승인 완료" sub="PTW-2026-0713-018" tone="cyan"/><Stat icon={ClipboardCheck} label="필수 조치" value="3 / 4 완료" sub="1건 확인 필요" tone="orange"/><Stat icon={Activity} label="현장 위험도" value="낮음 18" sub="전일 대비 -4" tone="green"/></div><div className="two-col"><Panel title="오늘의 작업 허가" action="상세보기"><div className="permit-card"><div className="permit-top"><span className="badge cyan">승인 완료</span><small>PTW-2026-0713-018</small></div><h3>B-07 블록 상부 배관 조립 작업</h3><div className="permit-meta"><span><Clock3/>08:00 - 17:00</span><span><Users/>조립 2팀 · 8명</span><span><Map/>B-07 / 3층</span></div><div className="condition"><ShieldCheck/><div><b>핵심 승인 조건</b><p>안전벨트 이중 체결 · 화기감시자 배치 · 작업반경 출입 통제</p></div></div></div></Panel><Panel title="작업 전 확인" action="4개 항목"><Task done text="TBM 브리핑 참여" time="07:43 완료"/><Task done text="개인 보호구 점검" time="07:48 완료"/><Task done text="작업 허가 조건 확인" time="07:51 완료"/><Task text="현장 도착 확인" time="작업 위치에서 확인" onClick={()=>notify("현장 도착이 확인되었습니다.")}/></Panel></div><div className="emergency" onClick={()=>notify("긴급 신고 화면으로 연결됩니다.")}><Siren/><div><b>현장에서 위험을 발견하셨나요?</b><span>사진이나 음성으로 즉시 신고하세요.</span></div><button>위험 신고하기 <Send/></button></div></>; }

function TBM({notify}) { const [recording,setRecording]=useState(false); const [lang,setLang]=useState("한국어"); return <><SectionHead eyebrow="TOOL BOX MEETING" title="TBM 안전 브리핑" desc="반장 발화를 실시간으로 기록하고 안전용어를 표준화합니다." action={<button className={recording?"danger-btn":"primary-small"} onClick={()=>setRecording(!recording)}>{recording?<><Radio/>녹음 중지</>:<><Mic/>브리핑 시작</>}</button>}/><div className="two-col tbm-layout"><Panel title="실시간 음성 인식" action={recording?"LIVE":"대기 중"}><div className={recording?"mic-stage recording":"mic-stage"}><div className="mic-orb"><Mic/></div><h3>{recording?"음성을 듣고 있습니다":"브리핑을 시작해 주세요"}</h3><p>{recording?"높은 곳에서 작업할 때는 안전대를 반드시 이중으로 체결하고…":"마이크 버튼을 누르면 한국어 음성 인식이 시작됩니다."}</p>{recording&&<div className="wave">{Array.from({length:28},(_,i)=><i key={i} style={{height:8+((i*17)%30)}}/>)}</div>}</div><div className="transcript"><span>AI 표준화 문장</span><p>고소 작업 시 안전벨트를 반드시 이중 체결하고, 작업 전 추락 방지 시설의 상태를 확인합니다.</p></div></Panel><Panel title="다국어 전달" action={<select value={lang} onChange={e=>setLang(e.target.value)}><option>한국어</option><option>English</option><option>Tiếng Việt</option><option>Русский</option></select>}><div className="language-card"><Languages/><div><span>{lang} 번역</span><p>{lang==="English"?"When working at height, always secure the safety harness twice and inspect fall protection facilities before work.":lang==="Tiếng Việt"?"Khi làm việc trên cao, luôn buộc dây an toàn hai lần và kiểm tra thiết bị chống rơi.":"고소 작업 시 안전벨트를 반드시 이중 체결하고 추락 방지 시설을 확인합니다."}</p></div></div><button className="outline-btn wide" onClick={()=>notify("선택한 언어로 음성을 재생합니다.")}><Headphones/>모국어 음성으로 듣기 <Play/></button><div className="understand"><h4>작업자 전달 확인</h4><div className="faces">{["김","이","응","팜","최","박","윤","장"].map((x,i)=><span className={i<6?"checked":""} key={i}>{i<6?<Check/>:x}</span>)}</div><p><b>6명 확인</b> · 2명 대기 중</p></div></Panel></div></>; }

function Checklist({notify}) { const [done,setDone]=useState([true,true,false,false]); const items=["안전벨트 및 생명줄 체결 상태 확인","작업구역 하부 출입 통제선 설치","화기감시자 배치 및 소화기 비치","이동식 사다리 고정 상태 확인"]; return <><SectionHead eyebrow="PERMIT CONDITIONS" title="조치 체크리스트" desc="허가서 승인 조건에 따라 작업 전 조치를 완료해 주세요."/><div className="single-panel"><div className="progress-head"><div><span>PTW-2026-0713-018</span><h3>B-07 블록 상부 배관 조립 작업</h3></div><b>{done.filter(Boolean).length} / 4 완료</b></div><div className="progress"><i style={{width:`${done.filter(Boolean).length*25}%`}}/></div><div className="check-list">{items.map((x,i)=><button key={x} className={done[i]?"done":""} onClick={()=>setDone(done.map((v,j)=>j===i?!v:v))}><span>{done[i]?<Check/>:i+1}</span><div><b>{x}</b><small>{done[i]?"확인 완료 · 김현수":"현장 확인 후 체크해 주세요"}</small></div><Camera/></button>)}</div><button className="primary-btn submit-check" onClick={()=>notify(done.every(Boolean)?"체크리스트가 제출되었습니다.":"모든 항목을 먼저 확인해 주세요.")}>체크리스트 제출</button></div></>; }

function Report({notify}) { const [type,setType]=useState("추락 위험"); return <><SectionHead eyebrow="QUICK SAFETY REPORT" title="현장 위험 신고" desc="발견한 위험을 사진 또는 음성으로 즉시 알려주세요."/><div className="report-layout"><div className="single-panel"><h3>위험 유형</h3><div className="chip-row">{["추락 위험","보호구 미착용","화재 위험","장비 이상","기타"].map(x=><button className={type===x?"active":""} onClick={()=>setType(x)} key={x}>{x}</button>)}</div><h3>사진 · 음성 첨부</h3><div className="upload-zone"><UploadCloud/><b>현장 사진을 끌어놓거나 촬영하세요</b><span>JPG, PNG · 최대 10MB</span><button className="outline-btn"><Camera/>카메라 열기</button></div><label className="text-label">상세 내용<textarea defaultValue="B-07 블록 3층 통로 난간 일부가 흔들립니다. 접근 통제가 필요합니다."/></label><button className="danger-submit" onClick={()=>notify("위험 신고가 안전관리자에게 전송되었습니다.")}><Siren/>긴급 위험 신고 전송</button></div><aside className="report-guide"><ShieldCheck/><h3>신고 즉시 처리됩니다</h3><p>긴급 신고는 관리자 관제 화면과 현장 담당자 모바일로 동시에 전송됩니다.</p><ol><li><b>1분 이내</b> 접수 알림</li><li><b>5분 이내</b> 담당자 배정</li><li>처리 결과 실시간 공유</li></ol></aside></div></>; }

function AdminHome() { return <><div className="welcome admin"><div><span className="eyebrow">CONTROL CENTER · LIVE</span><h2>조선소 통합 안전 현황</h2><p>거제 사업장 전체 구역의 실시간 위험 신호입니다.</p></div><div className="updated"><i/>마지막 갱신 10:45:18</div></div><div className="stat-grid"><Stat icon={Camera} label="연결 카메라" value="42 / 44" sub="2대 점검 중"/><Stat icon={AlertTriangle} label="오늘 감지 이벤트" value="18건" sub="긴급 1 · 주의 5" tone="orange"/><Stat icon={FileText} label="허가서 승인 대기" value="7건" sub="충돌 의심 2건" tone="cyan"/><Stat icon={Activity} label="전체 위험 지수" value="23 · 낮음" sub="어제보다 6 감소" tone="green"/></div><div className="admin-grid"><Panel title="실시간 사업장 맵" action="2.5D 위험맵"><div className="yard-map"><div className="map-grid"/>{[["A-12",22,22,"low"],["B-07",57,35,"high"],["C-03",73,64,"mid"],["D-02",35,72,"low"]].map(([n,x,y,c])=><div className={`map-pin ${c}`} style={{left:`${x}%`,top:`${y}%`}} key={n}><i/>{n}<small>{c==="high"?"위험 72":c==="mid"?"주의 46":"안전"}</small></div>)}</div></Panel><Panel title="실시간 이벤트" action="전체보기">{incidents.map(x=><div className="event-row" key={x.time+x.title}><span className={x.color}><AlertTriangle/></span><div><b>{x.title}</b><small>{x.meta}</small></div><time>{x.time}</time></div>)}</Panel></div><div className="two-col"><Panel title="위험도 추이" action="최근 7일"><div className="mini-chart">{[38,52,44,61,35,29,23].map((x,i)=><div key={i}><i style={{height:x*1.5}}/><span>{["월","화","수","목","금","토","오늘"][i]}</span></div>)}</div></Panel><Panel title="허가서 분석 현황" action="금일 24건"><div className="donut-wrap"><div className="donut"><span><b>24</b>전체</span></div><ul><li><i className="cyan"/>승인 완료 <b>15</b></li><li><i className="orange"/>검토 대기 <b>7</b></li><li><i className="red"/>충돌 의심 <b>2</b></li></ul></div></Panel></div></>; }

function Monitoring({notify}) { return <><SectionHead eyebrow="AI VISION CONTROL" title="실시간 영상 감시" desc="PPE 미착용과 위험구역 침입을 AI가 자동 감지합니다." action={<button className="outline-btn"><Settings/>관제 설정</button>}/><div className="monitor-grid">{["B-07 상부 작업장","C-03 배관 구역","A-12 도장 구역","D-02 자재 적치장"].map((x,i)=><div className="camera-card" key={x}><div className={`camera-feed cam${i+1}`}><div className="camera-head"><span><i/>LIVE · CAM-{[12,8,3,21][i]}</span><small>10:45:2{i}</small></div>{i===0&&<><div className="detect-box person"><span>PERSON 98%</span></div><div className="detect-box helmet"><span>NO HARNESS 94%</span></div></>}<div className="camera-name"><b>{x}</b><span>{i===0?"위험 이벤트 감지":"정상 모니터링"}</span></div></div>{i===0&&<button className="alert-action" onClick={()=>notify("현장 반장에게 경고를 전송했습니다.")}><Siren/>현장 경고 전송</button>}</div>)}</div></>; }

function Permits({notify}) { const [selected,setSelected]=useState(0); const rows=[{id:"PTW-2026-0713-024",name:"C-03 블록 배관 화기 작업",team:"배관 1팀",risk:"충돌 의심",tone:"red"},{id:"PTW-2026-0713-023",name:"B-11 블록 고소 조립 작업",team:"조립 4팀",risk:"AI 분석 완료",tone:"cyan"},{id:"PTW-2026-0713-022",name:"A-09 탱크 도장 작업",team:"도장 2팀",risk:"검토 대기",tone:"orange"}]; return <><SectionHead eyebrow="AI PERMIT ANALYSIS" title="작업 허가서 분석" desc="SIMOPS 충돌과 유사 사고를 분석해 승인 조건을 추천합니다." action={<button className="primary-small" onClick={()=>notify("허가서 업로드 창을 열었습니다.")}><Plus/>허가서 등록</button>}/><div className="permit-layout"><div className="permit-list"><div className="list-tools"><Search/><input placeholder="허가서, 작업명 검색"/></div>{rows.map((r,i)=><button className={selected===i?"selected":""} onClick={()=>setSelected(i)} key={r.id}><div><span className={`badge ${r.tone}`}>{r.risk}</span><small>{r.id}</small></div><b>{r.name}</b><span>{r.team} · 08:00-17:00</span></button>)}</div><div className="analysis-panel"><div className="analysis-head"><div><span>{rows[selected].id}</span><h3>{rows[selected].name}</h3></div><span className="ai-chip"><Sparkles/>AI 분석 96%</span></div><div className="doc-preview"><FileText/><div><b>작업허가서.pdf</b><span>12 pages · 2.4MB</span></div><button><Eye/></button></div><h4>SIMOPS 충돌 분석</h4><div className="collision"><AlertTriangle/><div><b>{selected===0?"동일 구역 동시 작업 1건 발견":"중대한 충돌이 없습니다"}</b><p>{selected===0?"C-03 하부에서 도장 작업이 09:00-12:00 예정되어 있습니다.":"시간·공간·작업 유형을 기준으로 확인했습니다."}</p></div></div><h4>AI 추천 승인 조건</h4>{["화기감시자 1인 이상 상시 배치","작업 반경 10m 내 가연물 제거","도장 작업 종료 후 가스 농도 측정"].map((x,i)=><label className="approval-item" key={x}><input type="checkbox" defaultChecked={i<2}/><span><b>{x}</b><small>산업안전보건기준 제{241+i}조 · 유사사고 8건</small></span></label>)}<div className="approve-actions"><button className="outline-btn">보완 요청</button><button className="primary-small" onClick={()=>notify("선택한 조건으로 허가서가 승인되었습니다.")}><Check/>조건부 승인</button></div></div></div></>; }

function Risk() { return <><SectionHead eyebrow="PREDICTIVE SAFETY" title="위험 예측" desc="작업 조합, 시간, PPE 착용률을 기반으로 사고 위험을 예측합니다."/><div className="risk-hero"><div><span>현재 사업장 위험 지수</span><strong>23<small>/100</small></strong><b>낮음 · 안정적</b></div><div className="gauge"><i/><span>0</span><span>100</span></div><div className="factors"><b>주요 영향 요인</b><p><span>고소 작업 집중도</span><i><em style={{width:"68%"}}/></i><strong>+12</strong></p><p><span>PPE 착용률</span><i><em style={{width:"91%"}}/></i><strong>-18</strong></p><p><span>동시 작업 충돌</span><i><em style={{width:"34%"}}/></i><strong>+7</strong></p></div></div><div className="block-risk"><h3>블록별 예측 위험도</h3>{[["B-07","높음",72,"red"],["C-03","주의",46,"orange"],["A-12","낮음",24,"cyan"],["D-02","낮음",18,"green"]].map(([n,l,v,c])=><div key={n}><b>{n}</b><span>{l}</span><i><em className={c} style={{width:`${v}%`}}/></i><strong>{v}</strong><button>What-if 분석</button></div>)}</div></>; }

function Standards({notify}) { return <><SectionHead eyebrow="SYSTEM STANDARD" title="기준 정보 관리" desc="ROI, 역할 권한, 조건 배포 정책을 관리합니다."/><div className="settings-grid"><Setting icon={Map} title="카메라 ROI 설정" text="44개 카메라의 위험구역 폴리곤 편집" value="42 적용"/><Setting icon={Users} title="역할 및 권한(RBAC)" text="현장 작업자와 관리자 접근 범위 관리" value="2개 역할"/><Setting icon={ShieldCheck} title="조건 배포 정책" text="Vision · 대시보드 · 체크리스트 매핑" value="18개 정책"/><Setting icon={Languages} title="안전용어 사전" text="TBM 현장 용어 표준화 및 다국어 사전" value="328개 용어"/></div><button className="primary-small save-settings" onClick={()=>notify("기준 정보가 저장되었습니다.")}><Check/>변경사항 저장</button></>; }
function Setting({icon:Icon,title,text,value}) { return <article className="setting-card"><div><Icon/></div><span><b>{title}</b><p>{text}</p><small>{value}</small></span><ChevronDown/></article>; }
function Audit() { return <><SectionHead eyebrow="PERMANENT RECORD" title="감사 로그" desc="판정 근거와 법령 출처를 변경 불가능한 기록으로 보관합니다."/><div className="single-panel audit-table"><div className="table-head"><span>시간</span><span>사용자</span><span>행위</span><span>대상 / 근거</span><span>상태</span></div>{[["10:42:18","AI Vision","PPE 위반 판정","EVT-8821 · 모델 v2.4.1","기록 완료"],["10:38:02","박서진","조건부 승인","PTW-2026-0713-021 · 제241조","기록 완료"],["10:21:44","김현수","체크리스트 제출","PTW-2026-0713-018","기록 완료"],["09:58:11","AI 분석","SIMOPS 충돌 판정","PTW-2026-0713-024 · RULE-18","검토 필요"]].map(r=><div className="table-row" key={r[0]}>{r.map((x,i)=><span key={i}>{x}</span>)}</div>)}</div></>; }

function SectionHead({eyebrow,title,desc,action}) { return <div className="section-head"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2><p>{desc}</p></div>{action}</div>; }
function Stat({icon:Icon,label,value,sub,tone="blue"}) { return <article className={`stat ${tone}`}><div><Icon/></div><span><small>{label}</small><b>{value}</b><em>{sub}</em></span></article>; }
function Panel({title,action,children}) { return <article className="panel"><div className="panel-head"><h3>{title}</h3><span>{action}</span></div>{children}</article>; }
function Task({done,text,time,onClick}) { return <button className={`task ${done?"done":""}`} onClick={onClick}><span>{done?<Check/>:""}</span><div><b>{text}</b><small>{time}</small></div><ChevronDown/></button>; }

createRoot(document.getElementById("root")).render(<App/>);
