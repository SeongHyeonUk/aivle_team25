import React, { useState } from "react";
import { Camera, Check } from "lucide-react";
import SectionHead from "../../components/common/SectionHead";

function Checklist({notify}) { const [done,setDone]=useState([true,true,false,false]); const items=["안전벨트 및 생명줄 체결 상태 확인","작업구역 하부 출입 통제선 설치","화기감시자 배치 및 소화기 비치","이동식 사다리 고정 상태 확인"]; return <><SectionHead eyebrow="PERMIT CONDITIONS" title="조치 체크리스트" desc="허가서 승인 조건에 따라 작업 전 조치를 완료해 주세요."/><div className="single-panel"><div className="progress-head"><div><span>PTW-2026-0713-018</span><h3>B-07 블록 상부 배관 조립 작업</h3></div><b>{done.filter(Boolean).length} / 4 완료</b></div><div className="progress"><i style={{width:`${done.filter(Boolean).length*25}%`}}/></div><div className="check-list">{items.map((x,i)=><button key={x} className={done[i]?"done":""} onClick={()=>setDone(done.map((v,j)=>j===i?!v:v))}><span>{done[i]?<Check/>:i+1}</span><div><b>{x}</b><small>{done[i]?"확인 완료 · 김현수":"현장 확인 후 체크해 주세요"}</small></div><Camera/></button>)}</div><button className="primary-btn submit-check" onClick={()=>notify(done.every(Boolean)?"체크리스트가 제출되었습니다.":"모든 항목을 먼저 확인해 주세요.")}>체크리스트 제출</button></div></>; }

export default Checklist;
