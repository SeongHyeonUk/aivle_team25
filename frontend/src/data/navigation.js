import { BarChart3, Camera, ClipboardCheck, FileSearch, FileText, LayoutDashboard, Mic, Settings, Siren } from "lucide-react";

const workerNav = [
  ["dashboard", "오늘의 작업", LayoutDashboard], ["tbm", "TBM 브리핑", Mic],
  ["checklist", "조치 체크리스트", ClipboardCheck], ["report", "위험 신고", Siren],
];
const adminNav = [
  ["dashboard", "통합 관제", LayoutDashboard], ["monitoring", "영상 감시", Camera],
  ["permits", "허가서 분석", FileSearch], ["risk", "위험 예측", BarChart3],
  ["standards", "기준 정보", Settings], ["audit", "감사 로그", FileText],
];

export { workerNav, adminNav };
