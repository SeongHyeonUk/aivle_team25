import React, { useState } from "react";
import { Bell, Building2, ChevronDown, Factory, LogOut, Menu, X } from "lucide-react";
import { adminNav, workerNav } from "../../data/navigation";
import Page from "./Page";

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

export default Dashboard;
