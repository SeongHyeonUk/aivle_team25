import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, Eye, FileText, Plus, Search, Sparkles, UploadCloud, X } from "lucide-react";
import { apiRequest } from "../../api/client";
import { SectionHead } from "../../components/common";

const emptyForm = () => ({
  permitNo: `PTW-${new Date().getFullYear()}-${Date.now().toString().slice(-6)}`,
  siteId: "",
  workType: "화기 작업",
  workTitle: "",
  workContent: "",
});

const formatSize = (bytes) => {
  if (!bytes) return "0 KB";
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;
};

function Permits({ notify, session }) {
  const [permits, setPermits] = useState([]);
  const [sites, setSites] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const authorization = useMemo(() => ({ Authorization: `Bearer ${session.token}` }), [session.token]);

  const loadPermits = async (preferredId) => {
    try {
      const rows = await apiRequest("/api/work-permits", { headers: authorization });
      setPermits(rows);
      setSelectedId(preferredId || rows[0]?.id || null);
    } catch (error) {
      notify(error.message);
    }
  };

  useEffect(() => {
    loadPermits();
    apiRequest("/api/master/sites", { headers: authorization })
      .then(rows => {
        setSites(rows);
        setForm(current => ({ ...current, siteId: current.siteId || String(rows[0]?.id || "") }));
      })
      .catch(error => notify(error.message));
  }, []);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    apiRequest(`/api/work-permits/${selectedId}`, { headers: authorization })
      .then(setDetail)
      .catch(error => notify(error.message));
  }, [selectedId]);

  const filtered = permits.filter(permit =>
    `${permit.permit_no || ""} ${permit.work_title || ""}`.toLowerCase().includes(search.toLowerCase())
  );

  const selectFile = (nextFile) => {
    if (!nextFile) return;
    if (nextFile.type !== "application/pdf" || !nextFile.name.toLowerCase().endsWith(".pdf")) return notify("PDF 허가서만 업로드할 수 있습니다.");
    if (nextFile.size > 10 * 1024 * 1024) return notify("허가서는 10MB 이하만 업로드할 수 있습니다.");
    setFile(nextFile);
  };

  const closeModal = (force = false) => {
    if (submitting && !force) return;
    setModalOpen(false);
    setFile(null);
    setForm({ ...emptyForm(), siteId: String(sites[0]?.id || "") });
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.siteId) return notify("등록된 사업장이 없습니다. 기준 정보에서 사업장을 먼저 등록해 주세요.");
    if (!form.permitNo.trim() || !form.workTitle.trim()) return notify("허가서 번호와 작업명을 입력해 주세요.");
    if (!file) return notify("허가서 PDF 파일을 선택해 주세요.");
    setSubmitting(true);
    try {
      const fileData = new FormData();
      fileData.append("file", file);
      fileData.append("fileType", "permit");
      const uploaded = await apiRequest("/api/files", { method: "POST", headers: authorization, body: fileData });
      const created = await apiRequest("/api/work-permits", {
        method: "POST",
        headers: authorization,
        body: JSON.stringify({
          ...form,
          siteId: Number(form.siteId),
          status: "pending_review",
          isHighRisk: false,
          fileIds: [uploaded.id],
        }),
      });
      closeModal(true);
      await loadPermits(created.id);
      notify(`${form.permitNo} 허가서가 등록되었습니다.`);
    } catch (error) {
      notify(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const attachedFile = detail?.files?.[0];
  return <>
    <SectionHead eyebrow="AI PERMIT ANALYSIS" title="작업 허가서 분석" desc="SIMOPS 충돌과 유사 사고를 분석해 승인 조건을 추천합니다." action={<button className="primary-small" onClick={() => setModalOpen(true)}><Plus/>허가서 등록</button>}/>
    <div className="permit-layout">
      <div className="permit-list">
        <div className="list-tools"><Search/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="허가서, 작업명 검색"/></div>
        {filtered.length ? filtered.map(permit => <button className={selectedId === permit.id ? "selected" : ""} onClick={() => setSelectedId(permit.id)} key={permit.id}><div><span className="badge orange">{permit.status === "pending_review" ? "검토 대기" : permit.status}</span><small>{permit.permit_no}</small></div><b>{permit.work_title || "작업명 미입력"}</b><span>{permit.work_type || "공종 미입력"}</span></button>) : <div className="permit-empty">등록된 허가서가 없습니다.</div>}
      </div>
      <div className="analysis-panel">
        {detail ? <><div className="analysis-head"><div><span>{detail.permit_no}</span><h3>{detail.work_title}</h3></div><span className="ai-chip"><Sparkles/>분석 대기</span></div>
          {attachedFile ? <div className="doc-preview"><FileText/><div><b>{attachedFile.original_name}</b><span>{formatSize(attachedFile.file_size)}</span></div><button title="파일 정보" onClick={() => notify(`${attachedFile.original_name} · ${formatSize(attachedFile.file_size)}`)}><Eye/></button></div> : <div className="doc-preview"><FileText/><div><b>첨부 파일 없음</b><span>허가서 파일이 연결되지 않았습니다.</span></div></div>}
          <h4>SIMOPS 충돌 분석</h4><div className="collision"><AlertTriangle/><div><b>AI 분석을 기다리고 있습니다</b><p>등록된 허가서를 기준으로 시간·공간·작업 유형을 분석합니다.</p></div></div>
          <h4>AI 추천 승인 조건</h4><div className="permit-empty">분석이 완료되면 추천 승인 조건이 표시됩니다.</div>
          <div className="approve-actions"><button className="outline-btn">보완 요청</button><button className="primary-small" onClick={() => notify("분석 완료 후 승인할 수 있습니다.")}><Check/>조건부 승인</button></div></> : <div className="permit-empty large">왼쪽에서 허가서를 선택하거나 새 허가서를 등록하세요.</div>}
      </div>
    </div>
    {modalOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) closeModal(); }}>
      <form className="permit-modal" role="dialog" aria-modal="true" aria-labelledby="permit-modal-title" onSubmit={submit}>
        <div className="modal-head"><div><span>WORK PERMIT</span><h3 id="permit-modal-title">허가서 등록</h3></div><button type="button" className="icon-btn" title="닫기" onClick={closeModal}><X/></button></div>
        <div className="permit-form-grid">
          <label><span>허가서 번호</span><input value={form.permitNo} onChange={e => setForm({ ...form, permitNo: e.target.value })}/></label>
          <label><span>사업장</span><select value={form.siteId} onChange={e => setForm({ ...form, siteId: e.target.value })}><option value="">사업장 선택</option>{sites.map(site => <option value={site.id} key={site.id}>{site.name}</option>)}</select></label>
          <label className="wide-field"><span>작업명</span><input value={form.workTitle} onChange={e => setForm({ ...form, workTitle: e.target.value })} placeholder="예: C-03 블록 배관 화기 작업"/></label>
          <label><span>작업 유형</span><select value={form.workType} onChange={e => setForm({ ...form, workType: e.target.value })}><option>화기 작업</option><option>고소 작업</option><option>밀폐 공간 작업</option><option>중량물 작업</option><option>일반 작업</option></select></label>
          <label className="wide-field"><span>작업 내용</span><textarea value={form.workContent} onChange={e => setForm({ ...form, workContent: e.target.value })} placeholder="작업 범위와 특이사항을 입력해 주세요."/></label>
        </div>
        <div className={file ? "permit-upload selected" : "permit-upload"} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); selectFile(e.dataTransfer.files[0]); }}><UploadCloud/><b>{file ? file.name : "허가서 PDF를 끌어놓으세요"}</b><span>{file ? formatSize(file.size) : "PDF · 최대 10MB"}</span><input id="permit-file" type="file" accept="application/pdf,.pdf" onChange={e => selectFile(e.target.files[0])}/><label htmlFor="permit-file" className="outline-btn">파일 선택</label></div>
        <div className="modal-actions"><button type="button" className="outline-btn" onClick={closeModal}>취소</button><button className="primary-small" disabled={submitting}>{submitting ? "등록 중..." : "업로드 및 등록"}</button></div>
      </form>
    </div>}
  </>;
}


export default Permits;
