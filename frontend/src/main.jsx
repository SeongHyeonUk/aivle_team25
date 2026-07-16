import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BarChart3,
  Camera,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  Factory,
  FileSearch,
  LockKeyhole,
  LogOut,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import "./styles.css";
import "./auth.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function apiRequest(path, options = {}) {
  let response;

  try {
    const isFormData = options.body instanceof FormData;

    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(!isFormData ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error(
      "백엔드 서버에 연결할 수 없습니다. MySQL과 Spring Boot 실행 상태를 확인해 주세요.",
    );
  }

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.message || "요청을 처리하지 못했습니다.");
  }

  return body;
}

function App() {
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("safety-session"));
    } catch {
      return null;
    }
  });

  const [authPage, setAuthPage] = useState("login");
  const [registeredUsername, setRegisteredUsername] = useState("");
  const [toast, setToast] = useState("");

  const notify = (message) => {
    setToast(message);
    window.clearTimeout(window.__toast);
    window.__toast = window.setTimeout(() => setToast(""), 2600);
  };

  const login = (nextSession) => {
    sessionStorage.setItem(
      "safety-session",
      JSON.stringify(nextSession),
    );
    setSession(nextSession);
    notify("로그인되었습니다.");
  };

  const logout = async () => {
    try {
      await apiRequest("/api/auth/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.token}`,
        },
      });
    } catch {
      // 서버 로그아웃에 실패하더라도 로컬 세션은 종료합니다.
    }

    sessionStorage.removeItem("safety-session");
    setSession(null);
    setAuthPage("login");
  };

  const registered = (username) => {
    setRegisteredUsername(username);
    setAuthPage("login");
    notify("회원가입이 완료되었습니다. 로그인해 주세요.");
  };

  return (
    <>
      {session ? (
        <AuthenticatedView session={session} onLogout={logout} />
      ) : authPage === "register" ? (
        <Register
          onBack={() => setAuthPage("login")}
          onRegistered={registered}
          notify={notify}
        />
      ) : (
        <Login
          initialUsername={registeredUsername}
          onRegister={() => setAuthPage("register")}
          onLogin={login}
          notify={notify}
        />
      )}

      {toast && (
        <div className="toast">
          <CheckCircle2 size={18} />
          {toast}
        </div>
      )}
    </>
  );
}

function VisualPanel() {
  return (
    <section className="visual-panel">
      <header className="brand">
        <Factory size={34} />
        <span>SMART SHIPYARD</span>
        <em>AI SAFETY</em>
      </header>

      <div className="hero-copy">
        <span className="eyebrow">CONNECTED SAFETY PLATFORM</span>
        <h1>
          AI 기반 스마트 조선소
          <br />
          <strong>안전관리 시스템</strong>
        </h1>
        <p>
          실시간 위험 감지부터 작업 허가, TBM까지.
          <br />
          조선소의 모든 안전 데이터를 하나로 연결합니다.
        </p>
      </div>

      <div className="scene">
        <div className="scan-grid" />
        <div className="pulse p1" />
        <div className="pulse p2" />
        <div className="float f1">
          <ShieldCheck /> PPE 감지 <b>정상</b>
        </div>
        <div className="float f2">
          <Camera /> CAM-12 <b>LIVE</b>
        </div>
        <div className="float f3">
          <Activity /> 위험도 <b>낮음</b>
        </div>
      </div>

      <div className="feature-strip">
        <Feature
          icon={Camera}
          title="AI 영상 관제"
          text="24시간 보호구·위험구역 감지"
        />
        <Feature
          icon={FileSearch}
          title="스마트 허가서"
          text="충돌 분석과 승인조건 자동 도출"
        />
        <Feature
          icon={BarChart3}
          title="예측 안전관리"
          text="블록별 위험도를 미리 확인"
        />
      </div>

      <footer>
        © 2026 Smart Shipyard AI Safety Management System
      </footer>
    </section>
  );
}

function Login({ initialUsername, onLogin, onRegister, notify }) {
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    username: initialUsername || "",
    password: "",
  });

  const submit = async (event) => {
    event.preventDefault();

    if (!form.username || !form.password) {
      notify("아이디와 비밀번호를 입력해 주세요.");
      return;
    }

    setSubmitting(true);

    try {
      const result = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(form),
      });

      const roles = result.user.roles || [];

      onLogin({
        token: result.accessToken,
        role: roles.includes("ADMIN") ? "admin" : "worker",
        name: result.user.name,
        username: result.user.username,
      });
    } catch (error) {
      notify(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <VisualPanel />

      <section className="login-wrap">
        <form className="login-card" onSubmit={submit}>
          <div className="login-head">
            <div className="shield-icon">
              <LockKeyhole />
            </div>

            <div>
              <span className="eyebrow">SECURE ACCESS</span>
              <h2>안전관리 시스템 로그인</h2>
              <p>허가된 임직원만 접속할 수 있습니다.</p>
            </div>
          </div>

          <label>
            <span>아이디</span>
            <div className="input-box">
              <UserRound />
              <input
                autoComplete="username"
                value={form.username}
                onChange={(event) =>
                  setForm({
                    ...form,
                    username: event.target.value,
                  })
                }
                placeholder="아이디를 입력하세요"
              />
            </div>
          </label>

          <label>
            <span>비밀번호</span>
            <div className="input-box">
              <LockKeyhole />
              <input
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={form.password}
                onChange={(event) =>
                  setForm({
                    ...form,
                    password: event.target.value,
                  })
                }
              />
              <button
                type="button"
                className="icon-btn"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </button>
            </div>
          </label>

          <div className="auth-actions">
            <button
              type="button"
              className="secondary-auth-btn"
              onClick={onRegister}
            >
              회원가입
            </button>

            <button
              className="primary-btn"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "접속 중..." : "시스템 접속 →"}
            </button>
          </div>

          <div className="login-note">
            <ShieldCheck />
            Spring Security · 역할 기반 접근 제어(RBAC)
          </div>
        </form>
      </section>
    </main>
  );
}

function Register({ onBack, onRegistered, notify }) {
  const [form, setForm] = useState({
    name: "",
    employeeNo: "",
    username: "",
    password: "",
    passwordConfirm: "",
  });

  const [employeeVerified, setEmployeeVerified] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const setField = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

    if (field === "name" || field === "employeeNo") {
      setEmployeeVerified(false);
    }

    if (field === "username") {
      setUsernameAvailable(false);
    }
  };

  const verifyEmployee = async () => {
    if (!form.name || !form.employeeNo) {
      notify("이름과 사번을 입력해 주세요.");
      return;
    }

    try {
      await apiRequest("/api/auth/employees/verify", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          employeeNo: form.employeeNo,
        }),
      });

      setEmployeeVerified(true);
      notify("사번 인증이 완료되었습니다.");
    } catch (error) {
      setEmployeeVerified(false);
      notify(error.message);
    }
  };

  const checkUsername = async () => {
    if (!form.username) {
      notify("아이디를 입력해 주세요.");
      return;
    }

    try {
      const result = await apiRequest(
        `/api/auth/usernames/${encodeURIComponent(form.username)}/availability`,
      );

      setUsernameAvailable(result.available);
      notify(
        result.available
          ? "사용할 수 있는 아이디입니다."
          : "이미 사용 중인 아이디입니다.",
      );
    } catch (error) {
      setUsernameAvailable(false);
      notify(error.message);
    }
  };

  const passwordValid = form.password.length >= 8;
  const passwordMatches =
    passwordValid && form.password === form.passwordConfirm;
  const canSubmit =
    employeeVerified && usernameAvailable && passwordMatches;

  const submit = async (event) => {
    event.preventDefault();

    if (!canSubmit) {
      notify("모든 입력과 인증을 완료해 주세요.");
      return;
    }

    setSubmitting(true);

    try {
      await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      });

      onRegistered(form.username);
    } catch (error) {
      notify(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <VisualPanel />

      <section className="login-wrap">
        <form
          className="login-card register-card"
          onSubmit={submit}
        >
          <div className="login-head">
            <div className="shield-icon">
              <UserRound />
            </div>

            <div>
              <span className="eyebrow">CREATE ACCOUNT</span>
              <h2>안전관리 시스템 회원가입</h2>
            </div>
          </div>

          <div className="register-row employee-row">
            <label>
              <span>이름</span>
              <div className="input-box">
                <UserRound />
                <input
                  value={form.name}
                  onChange={(event) =>
                    setField("name", event.target.value)
                  }
                />
                {employeeVerified && (
                  <CheckCircle2 className="field-check" />
                )}
              </div>
            </label>

            <label>
              <span>사번</span>
              <div className="input-box">
                <input
                  value={form.employeeNo}
                  onChange={(event) =>
                    setField("employeeNo", event.target.value)
                  }
                />
                {employeeVerified && (
                  <CheckCircle2 className="field-check" />
                )}
              </div>
            </label>

            <button
              type="button"
              className={
                employeeVerified
                  ? "verify-btn verified"
                  : "verify-btn"
              }
              onClick={verifyEmployee}
            >
              사번인증
              {employeeVerified && <Check />}
            </button>
          </div>

          <div className="register-row username-row">
            <label>
              <span>아이디</span>
              <div className="input-box">
                <UserRound />
                <input
                  value={form.username}
                  onChange={(event) =>
                    setField("username", event.target.value)
                  }
                />
                {usernameAvailable && (
                  <CheckCircle2 className="field-check" />
                )}
              </div>
            </label>

            <button
              type="button"
              className={
                usernameAvailable
                  ? "verify-btn verified"
                  : "verify-btn"
              }
              onClick={checkUsername}
            >
              중복체크
              {usernameAvailable && <Check />}
            </button>
          </div>

          <div className="register-row password-row">
            <label>
              <span>비밀번호</span>
              <div className="input-box">
                <LockKeyhole />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(event) =>
                    setField("password", event.target.value)
                  }
                />
                {passwordValid && (
                  <CheckCircle2 className="field-check" />
                )}
              </div>
            </label>

            <label>
              <span>비밀번호 확인</span>
              <div className="input-box">
                <LockKeyhole />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={form.passwordConfirm}
                  onChange={(event) =>
                    setField("passwordConfirm", event.target.value)
                  }
                />
                {passwordMatches && (
                  <CheckCircle2 className="field-check" />
                )}
              </div>
            </label>
          </div>

          <div className="auth-actions">
            <button
              type="button"
              className="secondary-auth-btn"
              onClick={onBack}
            >
              로그인으로
            </button>

            <button
              className="primary-btn"
              type="submit"
              disabled={!canSubmit || submitting}
            >
              {submitting
                ? "가입 처리 중..."
                : "회원가입 완료"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

function AuthenticatedView({ session, onLogout }) {
  return (
    <main className="login-page">
      <VisualPanel />

      <section className="login-wrap">
        <div className="login-card">
          <div className="login-head">
            <div className="shield-icon">
              <CheckCircle2 />
            </div>

            <div>
              <span className="eyebrow">LOGIN SUCCESS</span>
              <h2>{session.name}님, 로그인되었습니다.</h2>
              <p>{session.username}</p>
            </div>
          </div>

          <button
            type="button"
            className="primary-btn"
            onClick={onLogout}
          >
            <LogOut size={18} />
            로그아웃
          </button>
        </div>
      </section>
    </main>
  );
}

function Feature({ icon: Icon, title, text }) {
  return (
    <article>
      <Icon />
      <div>
        <b>{title}</b>
        <span>{text}</span>
      </div>
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
