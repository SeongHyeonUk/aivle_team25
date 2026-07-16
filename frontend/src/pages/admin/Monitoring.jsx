import React from "react";
import { Settings, Siren } from "lucide-react";
import SectionHead from "../../components/common/SectionHead";

function Monitoring({notify}) { return <><SectionHead eyebrow="AI VISION CONTROL" title="실시간 영상 감시" desc="PPE 미착용과 위험구역 침입을 AI가 자동 감지합니다." action={<button className="outline-btn"><Settings/>관제 설정</button>}/><div className="monitor-grid">{["B-07 상부 작업장","C-03 배관 구역","A-12 도장 구역","D-02 자재 적치장"].map((x,i)=><div className="camera-card" key={x}><div className={`camera-feed cam${i+1}`}><div className="camera-head"><span><i/>LIVE · CAM-{[12,8,3,21][i]}</span><small>10:45:2{i}</small></div>{i===0&&<><div className="detect-box person"><span>PERSON 98%</span></div><div className="detect-box helmet"><span>NO HARNESS 94%</span></div></>}<div className="camera-name"><b>{x}</b><span>{i===0?"위험 이벤트 감지":"정상 모니터링"}</span></div></div>{i===0&&<button className="alert-action" onClick={()=>notify("현장 반장에게 경고를 전송했습니다.")}><Siren/>현장 경고 전송</button>}</div>)}</div></>; }

export default Monitoring;
