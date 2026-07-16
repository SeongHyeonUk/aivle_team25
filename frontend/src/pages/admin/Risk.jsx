import React from "react";
import SectionHead from "../../components/common/SectionHead";

function Risk() { return <><SectionHead eyebrow="PREDICTIVE SAFETY" title="위험 예측" desc="작업 조합, 시간, PPE 착용률을 기반으로 사고 위험을 예측합니다."/><div className="risk-hero"><div><span>현재 사업장 위험 지수</span><strong>23<small>/100</small></strong><b>낮음 · 안정적</b></div><div className="gauge"><i/><span>0</span><span>100</span></div><div className="factors"><b>주요 영향 요인</b><p><span>고소 작업 집중도</span><i><em style={{width:"68%"}}/></i><strong>+12</strong></p><p><span>PPE 착용률</span><i><em style={{width:"91%"}}/></i><strong>-18</strong></p><p><span>동시 작업 충돌</span><i><em style={{width:"34%"}}/></i><strong>+7</strong></p></div></div><div className="block-risk"><h3>블록별 예측 위험도</h3>{[["B-07","높음",72,"red"],["C-03","주의",46,"orange"],["A-12","낮음",24,"cyan"],["D-02","낮음",18,"green"]].map(([n,l,v,c])=><div key={n}><b>{n}</b><span>{l}</span><i><em className={c} style={{width:`${v}%`}}/></i><strong>{v}</strong><button>What-if 분석</button></div>)}</div></>; }

export default Risk;
