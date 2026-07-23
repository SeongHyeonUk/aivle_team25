import React, { useState } from "react";
import { ChevronRight, Eye, EyeOff, FileText, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import { apiRequest } from "../../api/client";
import TermsModal from "../../components/auth/TermsModal";
import VisualPanel from "../../components/auth/VisualPanel";

function Login({ initialUsername, onLogin, onRegister, notify }) {
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const [form, setForm] = useState({ username: initialUsername || "", password: "" });

  const submit = async event => {
    event.preventDefault();
    if (!form.username || !form.password) return notify("\uC544\uC774\uB514\uC640 \uBE44\uBC00\uBC88\uD638\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694.");
    setSubmitting(true);
    try {
      const result = await apiRequest("/api/auth/login", { method: "POST", body: JSON.stringify(form) });
      const roles = result.user.roles || [];
      const isControlUser = roles.includes("ADMIN") || roles.includes("SAFETY_MANAGER");
      onLogin({ token: result.accessToken, role: isControlUser ? "admin" : "worker", name: result.user.name, username: result.user.username, roles });
    } catch (error) { notify(error.message); } finally { setSubmitting(false); }
  };

  return <>
    <main className="login-page"><VisualPanel /><section className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="login-head"><div className="shield-icon"><LockKeyhole /></div><div><span className="eyebrow">SECURE ACCESS</span><h2>{"\uC548\uC804\uAD00\uB9AC \uC2DC\uC2A4\uD15C \uB85C\uADF8\uC778"}</h2><p>{"\uD5C8\uAC00\uB41C \uC784\uC9C1\uC6D0\uB9CC \uC811\uC18D\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."}</p></div></div>
        <label><span>{"\uC544\uC774\uB514"}</span><div className="input-box"><UserRound /><input autoComplete="username" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} placeholder={"\uC544\uC774\uB514\uB97C \uC785\uB825\uD558\uC138\uC694"} /></div></label>
        <label><span>{"\uBE44\uBC00\uBC88\uD638"}</span><div className="input-box"><LockKeyhole /><input type={showPassword ? "text" : "password"} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder={"\uBE44\uBC00\uBC88\uD638\uB97C \uC785\uB825\uD558\uC138\uC694"} /><button type="button" className="icon-btn" onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff /> : <Eye />}</button></div></label>
        <div className="auth-actions"><button type="button" className="secondary-auth-btn" onClick={onRegister}>{"\uD68C\uC6D0\uAC00\uC785"}</button><button className="primary-btn" type="submit" disabled={submitting}>{submitting ? "\uC811\uC18D \uC911..." : "\uB85C\uADF8\uC778 \u2192"}</button></div>
        <div className="login-note"><ShieldCheck />Spring Security {"\u00B7 \uC5ED\uD560 \uAE30\uBC18 \uC811\uADFC \uC81C\uC5B4(RBAC)"}</div>
        <button type="button" className="terms-banner" onClick={() => setTermsOpen(true)}><FileText /><span><b>{"\uC11C\uBE44\uC2A4 \uC774\uC6A9\uC57D\uAD00"}</b><small>{"\uC57D\uAD00 \uBC0F \uAC1C\uC778\uC815\uBCF4 \uC218\uC9D1\u00B7\uC774\uC6A9 \uB0B4\uC6A9 \uD655\uC778"}</small></span><ChevronRight /></button>
      </form>
    </section></main>
    <TermsModal open={termsOpen} onClose={() => setTermsOpen(false)} />
  </>;
}

export default Login;
