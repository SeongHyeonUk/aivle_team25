import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { apiRequest } from "./api/client";
import Dashboard from "./components/layout/Dashboard";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

function App() {
  const [session, setSession] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("safety-session")); } catch { return null; }
  });
  const [authPage, setAuthPage] = useState("login");
  const [registeredUsername, setRegisteredUsername] = useState("");
  const [toast, setToast] = useState("");
  const notify = (message) => { setToast(message); window.clearTimeout(window.__toast); window.__toast = window.setTimeout(() => setToast(""), 2600); };
  const login = (nextSession) => { sessionStorage.setItem("safety-session", JSON.stringify(nextSession)); setSession(nextSession); };
  const logout = async () => {
    try { await apiRequest("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${session.token}` } }); } catch { /* local logout still proceeds */ }
    sessionStorage.removeItem("safety-session");
    setSession(null);
  };
  const registered = (username) => { setRegisteredUsername(username); setAuthPage("login"); notify("회원가입이 완료되었습니다. 로그인해 주세요."); };
  return <>{session
    ? <Dashboard session={session} onLogout={logout} notify={notify} />
    : authPage === "register"
      ? <Register onBack={() => setAuthPage("login")} onRegistered={registered} notify={notify} />
      : <Login initialUsername={registeredUsername} onRegister={() => setAuthPage("register")} onLogin={login} notify={notify} />}
    {toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}
  </>;
}

export default App;
