import { ClipboardCheck, Factory, FileSearch, LayoutDashboard, Mic, ShieldAlert, Siren } from "lucide-react";

const workerNav = [
  ["dashboard", "오늘의 작업", LayoutDashboard],
  ["tbm", "TBM 브리핑", Mic],
  ["checklist", "조치 체크리스트", ClipboardCheck],
  ["report", "위험 신고", Siren],
];

const adminNav = [
  ["dashboard", "디지털 트윈 관제", Factory],
  ["monitoring", "안전 이벤트", ShieldAlert],
  ["permits", "작업 허가", FileSearch],
];

export { workerNav, adminNav };
