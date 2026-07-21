import React, { useState } from "react";
import { Camera, ShieldCheck, Siren, UploadCloud } from "lucide-react";
import { SectionHead } from "../../components/common";

function Report({notify}) { const [type,setType]=useState("추락 위험"); return <><SectionHead eyebrow="QUICK SAFETY REPORT" title="현장 위험 신고" desc="발견한 위험을 사진 또는 음성으로 즉시 알려주세요."/><div className="report-layout"><div className="single-panel"><h3>위험 유형</h3><div className="chip-row">{["추락 위험","보호구 미착용","화재 위험","장비 이상","기타"].map(x=><button className={type===x?"active":""} onClick={()=>setType(x)} key={x}>{x}</button>)}</div><h3>사진 · 음성 첨부</h3><div className="upload-zone"><UploadCloud/><b>현장 사진을 끌어놓거나 촬영하세요</b><span>JPG, PNG · 최대 10MB</span><button className="outline-btn"><Camera/>카메라 열기</button></div><label className="text-label">상세 내용<textarea defaultValue="B-07 블록 3층 통로 난간 일부가 흔들립니다. 접근 통제가 필요합니다."/></label><button className="danger-submit" onClick={()=>notify("위험 신고가 안전관리자에게 전송되었습니다.")}><Siren/>긴급 위험 신고 전송</button></div><aside className="report-guide"><ShieldCheck/><h3>신고 즉시 처리됩니다</h3><p>긴급 신고는 관리자 관제 화면과 현장 담당자 모바일로 동시에 전송됩니다.</p><ol><li><b>1분 이내</b> 접수 알림</li><li><b>5분 이내</b> 담당자 배정</li><li>처리 결과 실시간 공유</li></ol></aside></div></>; }

export default Report;
