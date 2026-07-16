import React from "react";
import { Check, Languages, Map, ShieldCheck, Users } from "lucide-react";
import SectionHead from "../../components/common/SectionHead";
import Setting from "../../components/common/Setting";

function Standards({notify}) { return <><SectionHead eyebrow="SYSTEM STANDARD" title="기준 정보 관리" desc="ROI, 역할 권한, 조건 배포 정책을 관리합니다."/><div className="settings-grid"><Setting icon={Map} title="카메라 ROI 설정" text="44개 카메라의 위험구역 폴리곤 편집" value="42 적용"/><Setting icon={Users} title="역할 및 권한(RBAC)" text="현장 작업자와 관리자 접근 범위 관리" value="2개 역할"/><Setting icon={ShieldCheck} title="조건 배포 정책" text="Vision · 대시보드 · 체크리스트 매핑" value="18개 정책"/><Setting icon={Languages} title="안전용어 사전" text="TBM 현장 용어 표준화 및 다국어 사전" value="328개 용어"/></div><button className="primary-small save-settings" onClick={()=>notify("기준 정보가 저장되었습니다.")}><Check/>변경사항 저장</button></>; }

export default Standards;
