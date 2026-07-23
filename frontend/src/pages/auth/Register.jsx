import React, { useState } from "react";
import { Check, CheckCircle2, LockKeyhole, UserRound } from "lucide-react";
import { apiRequest } from "../../api/client";
import TermsModal from "../../components/auth/TermsModal";
import VisualPanel from "../../components/auth/VisualPanel";

const text = {
  nameEmployee: "\uC774\uB984\uACFC \uC0AC\uBC88\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694.",
  employeeDone: "\uC0AC\uBC88 \uC778\uC99D\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
  usernameRequired: "\uC544\uC774\uB514\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694.",
  usernameAvailable: "\uC0AC\uC6A9\uD560 \uC218 \uC788\uB294 \uC544\uC774\uB514\uC785\uB2C8\uB2E4.",
  usernameTaken: "\uC774\uBBF8 \uC0AC\uC6A9 \uC911\uC778 \uC544\uC774\uB514\uC785\uB2C8\uB2E4.",
  incomplete: "\uBAA8\uB4E0 \uC785\uB825\uACFC \uC778\uC99D, \uD544\uC218 \uC57D\uAD00 \uB3D9\uC758\uB97C \uC644\uB8CC\uD574 \uC8FC\uC138\uC694.",
};

function Register({ onBack, onRegistered, notify }) {
  const [form, setForm] = useState({ name: "", employeeNo: "", username: "", password: "", passwordConfirm: "" });
  const [employeeVerified, setEmployeeVerified] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const setField = (field, value) => {
    setForm(current => ({ ...current, [field]: value }));
    if (field === "name" || field === "employeeNo") setEmployeeVerified(false);
    if (field === "username") setUsernameAvailable(false);
  };

  const verifyEmployee = async () => {
    if (!form.name || !form.employeeNo) return notify(text.nameEmployee);
    try {
      await apiRequest("/api/auth/employees/verify", { method: "POST", body: JSON.stringify({ name: form.name, employeeNo: form.employeeNo }) });
      setEmployeeVerified(true);
      notify(text.employeeDone);
    } catch (error) { setEmployeeVerified(false); notify(error.message); }
  };

  const checkUsername = async () => {
    if (!form.username) return notify(text.usernameRequired);
    try {
      const result = await apiRequest(`/api/auth/usernames/${encodeURIComponent(form.username)}/availability`);
      setUsernameAvailable(result.available);
      notify(result.available ? text.usernameAvailable : text.usernameTaken);
    } catch (error) { setUsernameAvailable(false); notify(error.message); }
  };

  const passwordValid = form.password.length >= 8;
  const passwordMatches = passwordValid && form.password === form.passwordConfirm;
  const canSubmit = employeeVerified && usernameAvailable && passwordMatches && termsAgreed;

  const submit = async event => {
    event.preventDefault();
    if (!canSubmit) return notify(text.incomplete);
    setSubmitting(true);
    try {
      await apiRequest("/api/auth/register/admin", { method: "POST", body: JSON.stringify({ ...form, termsAgreed }) });
      onRegistered(form.username);
    } catch (error) { notify(error.message); } finally { setSubmitting(false); }
  };

  return <>
    <main className="login-page"><VisualPanel /><section className="login-wrap">
      <form className="login-card register-card" onSubmit={submit}>
        <div className="login-head"><div className="shield-icon"><UserRound /></div><div><span className="eyebrow">CREATE ACCOUNT</span><h2>{"\uD68C\uC6D0\uAC00\uC785"}</h2><p>{"\uC0AC\uBC88 \uC778\uC99D \uD6C4 \uACC4\uC815\uC744 \uC0DD\uC131\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."}</p></div></div>
        <div className="register-row employee-row">
          <label><span>{"\uC774\uB984"}</span><div className="input-box"><UserRound /><input value={form.name} onChange={e => setField("name", e.target.value)} />{employeeVerified && <CheckCircle2 className="field-check" />}</div></label>
          <label><span>{"\uC0AC\uBC88"}</span><div className="input-box"><input value={form.employeeNo} onChange={e => setField("employeeNo", e.target.value)} />{employeeVerified && <CheckCircle2 className="field-check" />}</div></label>
          <button type="button" className={employeeVerified ? "verify-btn verified" : "verify-btn"} onClick={verifyEmployee}>{"\uC0AC\uBC88 \uC778\uC99D"}{employeeVerified && <Check />}</button>
        </div>
        <div className="register-row username-row"><label><span>{"\uC544\uC774\uB514"}</span><div className="input-box"><UserRound /><input value={form.username} onChange={e => setField("username", e.target.value)} />{usernameAvailable && <CheckCircle2 className="field-check" />}</div></label><button type="button" className={usernameAvailable ? "verify-btn verified" : "verify-btn"} onClick={checkUsername}>{"\uC911\uBCF5 \uCCB4\uD06C"}{usernameAvailable && <Check />}</button></div>
        <div className="register-row password-row">
          <label><span>{"\uBE44\uBC00\uBC88\uD638"}</span><div className="input-box"><LockKeyhole /><input type="password" autoComplete="new-password" value={form.password} onChange={e => setField("password", e.target.value)} />{passwordValid && <CheckCircle2 className="field-check" />}</div></label>
          <label><span>{"\uBE44\uBC00\uBC88\uD638 \uD655\uC778"}</span><div className="input-box"><LockKeyhole /><input type="password" autoComplete="new-password" value={form.passwordConfirm} onChange={e => setField("passwordConfirm", e.target.value)} />{passwordMatches && <CheckCircle2 className="field-check" />}</div></label>
        </div>
        <div className="terms-consent"><label><input type="checkbox" checked={termsAgreed} onChange={e => setTermsAgreed(e.target.checked)} /><span><b>{"[\uD544\uC218]"}</b>{" \uC774\uC6A9\uC57D\uAD00 \uBC0F \uAC1C\uC778\uC815\uBCF4 \uC218\uC9D1\u00B7\uC774\uC6A9\uC5D0 \uB3D9\uC758\uD569\uB2C8\uB2E4."}</span></label><button type="button" onClick={() => setTermsOpen(true)}>{"\uB0B4\uC6A9 \uBCF4\uAE30"}</button></div>
        <div className="auth-actions"><button type="button" className="secondary-auth-btn" onClick={onBack}>{"\uB85C\uADF8\uC778\uC73C\uB85C"}</button><button className="primary-btn" type="submit" disabled={!canSubmit || submitting}>{submitting ? "\uAC00\uC785 \uCC98\uB9AC \uC911..." : "\uD68C\uC6D0\uAC00\uC785"}</button></div>
      </form>
    </section></main>
    <TermsModal open={termsOpen} onClose={() => setTermsOpen(false)} />
  </>;
}

export default Register;
