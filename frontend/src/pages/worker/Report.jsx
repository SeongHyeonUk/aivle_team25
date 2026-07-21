import React, { useEffect, useState } from "react";
import { Camera, ShieldCheck, Siren, UploadCloud } from "lucide-react";
import { apiRequest } from "../../api/client";
import { SectionHead } from "../../components/common";

const riskReportTypes = [
  ["FALL_HEIGHT", "추락·고소작업 위험"],
  ["PPE_MISSING", "보호구 미착용"],
  ["FIRE_EXPLOSION", "화재·폭발 위험"],
  ["EQUIPMENT_FAILURE", "장비·설비 이상"],
  ["COLLISION_PINCH", "충돌·협착 위험"],
  ["FALLING_OBJECT_LIFTING", "낙하물·중량물 위험"],
  ["ELECTRICAL", "감전·전기 위험"],
  ["ASPHYXIATION_GAS", "질식·유해가스 위험"],
  ["HAZARDOUS_LEAK", "위험물·화학물질 누출"],
  ["DANGER_ZONE_ACCESS", "위험구역 접근"],
  ["HOUSEKEEPING", "통로·정리정돈 불량"],
  ["OTHER", "기타"],
];

function Report({notify,session}) {
  const [type,setType]=useState("FALL_HEIGHT");
  const [photo,setPhoto]=useState(null);
  const [description,setDescription]=useState("");
  const [reports,setReports]=useState([]);
  const [loadingReports,setLoadingReports]=useState(true);
  const [submitting,setSubmitting]=useState(false);
  const [preview,setPreview]=useState("");
  const authorization = { Authorization:`Bearer ${session.token}` };

  const loadReports = async () => {
    setLoadingReports(true);
    try {
      setReports(await apiRequest("/api/safety-events/my", { headers:authorization }));
    } catch (error) {
      notify(error.message);
    } finally {
      setLoadingReports(false);
    }
  };

  useEffect(() => { loadReports(); }, []);
  useEffect(() => {
    if (!photo) { setPreview(""); return undefined; }
    const nextPreview = URL.createObjectURL(photo);
    setPreview(nextPreview);
    return () => URL.revokeObjectURL(nextPreview);
  }, [photo]);

  const selectPhoto = (file) => {
    if (!file) return;
    if (!["image/jpeg","image/png"].includes(file.type)) return notify("JPG 또는 PNG 사진만 첨부할 수 있습니다.");
    if (file.size > 10 * 1024 * 1024) return notify("사진은 10MB 이하만 첨부할 수 있습니다.");
    setPhoto(file);
  };

  const submit = async () => {
    if (!photo) return notify("현장 사진을 첨부해 주세요.");
    if (!description.trim()) return notify("상세 내용을 입력해 주세요.");
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", photo);
      formData.append("fileType", "safety_report");
      const uploaded = await apiRequest("/api/files", { method:"POST", headers:authorization, body:formData });
      const created = await apiRequest("/api/safety-events", {
        method:"POST",
        headers:authorization,
        body:JSON.stringify({ eventType:type, fileId:uploaded.id, description:description.trim() }),
      });
      notify(`${created.reportNo} 위험 신고가 접수되었습니다.`);
      setPhoto(null);
      setDescription("");
      await loadReports();
    } catch (error) {
      notify(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const latest = reports[0];
  return <>
    <SectionHead eyebrow="QUICK SAFETY REPORT" title="현장 위험 신고" desc="위험 유형을 선택하고 현장 사진과 상세 내용을 접수해 주세요."/>
    <div className="report-layout">
      <div className="single-panel">
        <h3>위험 유형</h3>
        <div className="chip-row">{riskReportTypes.map(([code,label])=><button type="button" className={type===code?"active":""} onClick={()=>setType(code)} key={code}>{label}</button>)}</div>
        <h3>사진 첨부</h3>
        <div className={preview?"upload-zone has-preview":"upload-zone"} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();selectPhoto(e.dataTransfer.files[0]);}}>
          {preview?<img src={preview} alt="위험 신고 사진 미리보기"/>:<><UploadCloud/><b>현장 사진을 끌어놓거나 촬영하세요</b><span>JPG, PNG · 최대 10MB</span></>}
          <input id="risk-photo" type="file" accept="image/jpeg,image/png" capture="environment" onChange={e=>selectPhoto(e.target.files[0])}/>
          <label htmlFor="risk-photo" className="outline-btn upload-button"><Camera/>{photo?"사진 변경":"폴더 열기"}</label>
          {photo&&<small className="selected-file">{photo.name}</small>}
        </div>
        <label className="text-label">상세 내용<textarea value={description} maxLength={2000} placeholder="위험 상황과 위치를 구체적으로 작성해 주세요." onChange={e=>setDescription(e.target.value)}/></label>
        <button className="danger-submit" disabled={submitting} onClick={submit}><Siren/>{submitting?"신고 접수 중...":"위험 신고 접수"}</button>
      </div>
      <aside className="report-guide report-status">
        <ShieldCheck/>
        <h3>내 신고 현황</h3>
        {loadingReports?<p>신고 내역을 불러오는 중입니다.</p>:<>
          <div className="report-count"><span>최근 신고</span><b>{reports.length}<small>건</small></b></div>
          {latest?<div className="latest-report"><span className="badge cyan">접수 완료</span><b>{latest.title}</b><small>{latest.reportNo}</small><p>{latest.description}</p></div>:<div className="empty-report">접수한 위험 신고가 없습니다.</div>}
        </>}
      </aside>
    </div>
  </>;
}

export default Report;
