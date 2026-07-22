import React, { useState } from "react";
import { Bell, Factory, LogOut, Menu, X } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { adminNav } from "../../data/navigation";
import Page from "./Page";

function Dashboard({ session, onLogout, notify }) {
  const navigate = useNavigate();
  const { page = "dashboard" } = useParams();
  const [mobile, setMobile] = useState(false);
  const nav = adminNav;
  const title = nav.find(n=>n[0]===page)?.[1] || "대시보드";
  return <div className="app-shell">
    <aside className={mobile?"sidebar open":"sidebar"}><div className="side-brand"><Factory/><div><b>SMART SHIPYARD</b><span>AI SAFETY PLATFORM</span></div><button onClick={()=>setMobile(false)}><X/></button></div><nav>{nav.map(([id,label,Icon])=><button key={id} className={page===id?"active":""} onClick={()=>{navigate(`/admin/${id}`);setMobile(false)}}><Icon/>{label}</button>)}</nav><div className="side-bottom"><div className="user-chip"><div>{session.name[0]}</div><span><b>{session.name}</b><small>안전관리자 · 안전환경팀</small></span></div><button className="logout" onClick={onLogout}><LogOut/>로그아웃</button></div></aside>
    <main className="workspace"><header className="topbar"><button className="menu-btn" onClick={()=>setMobile(true)}><Menu/></button><div><span>거제 스마트 조선소 / 관리자</span><h1>{title}</h1></div><div className="top-actions"><div className="live"><i/> 시스템 정상</div><button><Bell/><i>3</i></button><div className="avatar">{session.name[0]}</div></div></header>
      <section className="content"><Page page={page} session={session} notify={notify}/></section>
    </main>
  </div>;
}

export default Dashboard;
