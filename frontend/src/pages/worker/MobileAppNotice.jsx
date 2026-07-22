import React from "react";
import { LogOut, Smartphone } from "lucide-react";
import VisualPanel from "../../components/auth/VisualPanel";

function MobileAppNotice({ session, onLogout }) {
  return <main className="login-page">
    <VisualPanel/>
    <section className="login-wrap">
      <div className="login-card mobile-app-notice">
        <div className="mobile-app-icon"><Smartphone/></div>
        <span className="eyebrow">MOBILE SERVICE</span>
        <h2>{session.name} 님</h2>
        <p>현장 작업자 기능은 모바일 앱을 이용해 주세요.</p>
        <button type="button" className="secondary-auth-btn" onClick={onLogout}><LogOut/>로그아웃</button>
      </div>
    </section>
  </main>;
}

export default MobileAppNotice;
