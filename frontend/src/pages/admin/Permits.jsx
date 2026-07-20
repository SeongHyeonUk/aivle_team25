<<<<<<< Updated upstream
import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  Eye,
  FileText,
  Plus,
  Search,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import SectionHead from "../../components/common/SectionHead";

const initialPermits = [
  {
    id: "PTW-2026-0713-024",
    name: "C-03 블록 배관 화기 작업",
    team: "배관 1팀",
    time: "08:00-17:00",
    risk: "충돌 의심",
    tone: "red",
    fileName: "작업허가서.pdf",
    fileSize: "2.4 MB",
    fileUrl: "",
  },
  {
    id: "PTW-2026-0713-023",
    name: "B-11 블록 고소 조립 작업",
    team: "조립 4팀",
    time: "08:00-17:00",
    risk: "AI 분석 완료",
    tone: "cyan",
    fileName: "고소작업허가서.pdf",
    fileSize: "1.8 MB",
    fileUrl: "",
  },
  {
    id: "PTW-2026-0713-022",
    name: "A-09 탱크 도장 작업",
    team: "도장 2팀",
    time: "08:00-17:00",
    risk: "검토 대기",
    tone: "orange",
    fileName: "도장작업허가서.pdf",
    fileSize: "1.2 MB",
    fileUrl: "",
  },
];
=======
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
>>>>>>> Stashed changes

const initialConditions = [
  {
    id: 1,
    text: "화기감시자 1인 이상 상시 배치",
    reference: "산업안전보건기준 제241조 · 유사사고 8건",
    checked: true,
  },
  {
    id: 2,
    text: "작업 반경 10m 내 가연물 제거",
    reference: "산업안전보건기준 제242조 · 유사사고 8건",
    checked: true,
  },
  {
    id: 3,
    text: "도장 작업 종료 후 가스 농도 측정",
    reference: "산업안전보건기준 제243조 · 유사사고 8건",
    checked: false,
  },
];

function formatFileSize(size) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function createPermitId() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const number = String(Math.floor(Math.random() * 900) + 100);

  return `PTW-${year}-${month}${day}-${number}`;
}

function Permits({ notify }) {
  const fileInputRef = useRef(null);

  const [permits, setPermits] = useState(initialPermits);
  const [selectedPermitId, setSelectedPermitId] = useState(
    initialPermits[0].id,
  );
  const [searchKeyword, setSearchKeyword] = useState("");

  const [uploadOpen, setUploadOpen] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const [uploadForm, setUploadForm] = useState({
    name: "",
    team: "",
    time: "08:00-17:00",
    file: null,
  });

  const [conditions, setConditions] = useState(initialConditions);

  const selectedPermit =
    permits.find((permit) => permit.id === selectedPermitId) ??
    permits[0] ??
    null;

  const filteredPermits = permits.filter((permit) => {
    const keyword = searchKeyword.trim().toLowerCase();

    if (!keyword) {
      return true;
    }

    return (
      permit.id.toLowerCase().includes(keyword) ||
      permit.name.toLowerCase().includes(keyword) ||
      permit.team.toLowerCase().includes(keyword)
    );
  });

  const showNotification = (message) => {
    if (typeof notify === "function") {
      notify(message);
      return;
    }

    window.alert(message);
  };

  const resetUploadForm = () => {
    setUploadForm({
      name: "",
      team: "",
      time: "08:00-17:00",
      file: null,
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const closeUploadModal = () => {
    setUploadOpen(false);
    setDragActive(false);
    resetUploadForm();
  };

  const handleFile = (file) => {
    if (!file) {
      return;
    }

    const allowedExtensions = [
      "pdf",
      "png",
      "jpg",
      "jpeg",
      "doc",
      "docx",
    ];

    const extension = file.name
      .split(".")
      .pop()
      ?.toLowerCase();

    if (!extension || !allowedExtensions.includes(extension)) {
      showNotification(
        "PDF, JPG, PNG, DOC, DOCX 파일만 업로드할 수 있습니다.",
      );
      return;
    }

    const maximumSize = 20 * 1024 * 1024;

    if (file.size > maximumSize) {
      showNotification("파일 크기는 20MB 이하만 가능합니다.");
      return;
    }

    setUploadForm((previous) => ({
      ...previous,
      file,
    }));
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];

    handleFile(selectedFile);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);

    const droppedFile = event.dataTransfer.files?.[0];

    handleFile(droppedFile);
  };

  const handleUpload = (event) => {
    event.preventDefault();

    if (!uploadForm.name.trim()) {
      showNotification("작업명을 입력해 주세요.");
      return;
    }

    if (!uploadForm.team.trim()) {
      showNotification("작업팀을 입력해 주세요.");
      return;
    }

    if (!uploadForm.file) {
      showNotification("허가서 파일을 선택해 주세요.");
      return;
    }

    const newPermitId = createPermitId();
    const fileUrl = URL.createObjectURL(uploadForm.file);

    const newPermit = {
      id: newPermitId,
      name: uploadForm.name.trim(),
      team: uploadForm.team.trim(),
      time: uploadForm.time.trim() || "08:00-17:00",
      risk: "AI 분석 대기",
      tone: "orange",
      fileName: uploadForm.file.name,
      fileSize: formatFileSize(uploadForm.file.size),
      fileUrl,
    };

    setPermits((previousPermits) => [
      newPermit,
      ...previousPermits,
    ]);

    setSelectedPermitId(newPermitId);
    setConditions(initialConditions);

    setUploadOpen(false);
    setDragActive(false);

    resetUploadForm();

    showNotification("허가서가 등록되었습니다.");
  };

  const handlePermitSelect = (permitId) => {
    setSelectedPermitId(permitId);
    setConditions(initialConditions);
  };

  const handleConditionChange = (conditionId) => {
    setConditions((previousConditions) =>
      previousConditions.map((condition) =>
        condition.id === conditionId
          ? {
              ...condition,
              checked: !condition.checked,
            }
          : condition,
      ),
    );
  };

  const handleFilePreview = () => {
    if (!selectedPermit) {
      return;
    }

    if (!selectedPermit.fileUrl) {
      showNotification(
        "기본으로 등록된 샘플 허가서는 미리보기를 지원하지 않습니다.",
      );
      return;
    }

    window.open(
      selectedPermit.fileUrl,
      "_blank",
      "noopener,noreferrer",
    );
  };

  return (
    <>
      <SectionHead
        eyebrow="AI PERMIT ANALYSIS"
        title="작업 허가서 분석"
        desc="SIMOPS 충돌과 유사 사고를 분석해 승인 조건을 추천합니다."
        action={
          <button
            type="button"
            className="permit-register-button"
            onClick={() => setUploadOpen(true)}
          >
            <Plus />
            허가서 등록
          </button>
        }
      />

      <div className="permit-analysis-layout">
        <aside className="permit-sidebar-panel">
          <div className="permit-search">
            <Search />

            <input
              value={searchKeyword}
              onChange={(event) =>
                setSearchKeyword(event.target.value)
              }
              placeholder="허가서, 작업명 검색"
            />
          </div>

          <div className="permit-list-items">
            {filteredPermits.map((permit) => (
              <button
                type="button"
                key={permit.id}
                className={
                  selectedPermit?.id === permit.id
                    ? "permit-list-item selected"
                    : "permit-list-item"
                }
                onClick={() =>
                  handlePermitSelect(permit.id)
                }
              >
                <div className="permit-list-status">
                  <span
                    className={`permit-status-badge ${permit.tone}`}
                  >
                    {permit.risk}
                  </span>

                  <small>{permit.id}</small>
                </div>

                <strong>{permit.name}</strong>

                <span>
                  {permit.team} · {permit.time}
                </span>
              </button>
            ))}

            {filteredPermits.length === 0 && (
              <div className="permit-empty-search">
                검색 결과가 없습니다.
              </div>
            )}
          </div>
        </aside>

        {selectedPermit ? (
          <section className="permit-detail-panel">
            <div className="permit-detail-header">
              <div>
                <span>{selectedPermit.id}</span>
                <h3>{selectedPermit.name}</h3>
              </div>

              <div className="permit-ai-score">
                <Sparkles />
                AI 분석 96%
              </div>
            </div>

            <div className="permit-document-card">
              <div className="permit-file-icon">
                <FileText />
              </div>

              <div className="permit-file-info">
                <strong>{selectedPermit.fileName}</strong>

                <span>
                  {selectedPermit.fileSize} ·{" "}
                  {selectedPermit.team}
                </span>
              </div>

              <button
                type="button"
                className="permit-preview-button"
                onClick={handleFilePreview}
                aria-label="허가서 파일 미리보기"
              >
                <Eye />
              </button>
            </div>

            <div className="permit-analysis-section">
              <h4>SIMOPS 충돌 분석</h4>

              <div
                className={
                  selectedPermit.risk === "충돌 의심"
                    ? "permit-collision warning"
                    : "permit-collision normal"
                }
              >
                <AlertTriangle />

                <div>
                  <strong>
                    {selectedPermit.risk === "충돌 의심"
                      ? "동일 구역 동시 작업 1건 발견"
                      : selectedPermit.risk ===
                          "AI 분석 대기"
                        ? "업로드한 허가서를 분석 중입니다"
                        : "중대한 작업 충돌이 없습니다"}
                  </strong>

                  <p>
                    {selectedPermit.risk === "충돌 의심"
                      ? "C-03 하부에서 도장 작업이 09:00-12:00 예정되어 있습니다."
                      : selectedPermit.risk ===
                          "AI 분석 대기"
                        ? "파일 업로드가 완료되었습니다. 작업 시간과 구역 정보를 분석합니다."
                        : "시간, 공간, 작업 유형을 기준으로 허가서를 분석했습니다."}
                  </p>
                </div>
              </div>
            </div>

            <div className="permit-analysis-section">
              <h4>AI 추천 승인 조건</h4>

              <div className="permit-condition-list">
                {conditions.map((condition) => (
                  <label
                    className="permit-condition-item"
                    key={condition.id}
                  >
                    <input
                      type="checkbox"
                      checked={condition.checked}
                      onChange={() =>
                        handleConditionChange(
                          condition.id,
                        )
                      }
                    />

                    <span className="permit-custom-checkbox">
                      {condition.checked && <Check />}
                    </span>

                    <span className="permit-condition-text">
                      <strong>{condition.text}</strong>
                      <small>{condition.reference}</small>
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="permit-detail-actions">
              <button
                type="button"
                className="permit-request-button"
                onClick={() =>
                  showNotification(
                    "허가서 보완 요청을 전송했습니다.",
                  )
                }
              >
                보완 요청
              </button>

              <button
                type="button"
                className="permit-approve-button"
                onClick={() =>
                  showNotification(
                    "선택한 승인 조건으로 허가서를 승인했습니다.",
                  )
                }
              >
                <Check />
                조건부 승인
              </button>
            </div>
          </section>
        ) : (
          <section className="permit-detail-panel">
            <div className="permit-empty-search">
              등록된 허가서가 없습니다.
            </div>
          </section>
        )}
      </div>

      {uploadOpen && (
        <div
          className="permit-upload-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeUploadModal();
            }
          }}
        >
          <form
            className="permit-upload-modal"
            onSubmit={handleUpload}
          >
            <div className="permit-upload-header">
              <div>
                <span>NEW WORK PERMIT</span>
                <h3>작업 허가서 등록</h3>
                <p>
                  허가서 파일과 작업 정보를 등록해 주세요.
                </p>
              </div>

              <button
                type="button"
                className="permit-modal-close"
                onClick={closeUploadModal}
                aria-label="업로드 창 닫기"
              >
                <X />
              </button>
            </div>

            <div className="permit-upload-fields">
              <label>
                <span>작업명</span>

                <input
                  value={uploadForm.name}
                  onChange={(event) =>
                    setUploadForm((previous) => ({
                      ...previous,
                      name: event.target.value,
                    }))
                  }
                  placeholder="예: C-03 블록 배관 화기 작업"
                />
              </label>

              <div className="permit-upload-field-row">
                <label>
                  <span>작업팀</span>

                  <input
                    value={uploadForm.team}
                    onChange={(event) =>
                      setUploadForm((previous) => ({
                        ...previous,
                        team: event.target.value,
                      }))
                    }
                    placeholder="예: 배관 1팀"
                  />
                </label>

                <label>
                  <span>작업 시간</span>

                  <input
                    value={uploadForm.time}
                    onChange={(event) =>
                      setUploadForm((previous) => ({
                        ...previous,
                        time: event.target.value,
                      }))
                    }
                    placeholder="08:00-17:00"
                  />
                </label>
              </div>
            </div>

            <div
              className={
                dragActive
                  ? "permit-file-dropzone active"
                  : "permit-file-dropzone"
              }
              onDragEnter={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setDragActive(false);
              }}
              onDrop={handleDrop}
              onClick={() =>
                fileInputRef.current?.click()
              }
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                onChange={handleFileChange}
                hidden
              />

              <UploadCloud />

              {uploadForm.file ? (
                <>
                  <strong>{uploadForm.file.name}</strong>

                  <span>
                    {formatFileSize(
                      uploadForm.file.size,
                    )}
                  </span>

                  <small>
                    다른 파일을 선택하려면 클릭하세요.
                  </small>
                </>
              ) : (
                <>
                  <strong>
                    허가서 파일을 끌어놓거나 선택하세요
                  </strong>

                  <span>
                    PDF, JPG, PNG, DOC, DOCX · 최대
                    20MB
                  </span>

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    파일 선택
                  </button>
                </>
              )}
            </div>

            <div className="permit-upload-actions">
              <button
                type="button"
                className="permit-upload-cancel"
                onClick={closeUploadModal}
              >
                취소
              </button>

              <button
                type="submit"
                className="permit-upload-submit"
              >
                <UploadCloud />
                허가서 업로드
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

export default Permits;