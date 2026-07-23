import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { apiRequest } from "./api/client";
import Dashboard from "./components/layout/Dashboard";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

function App() {
  const navigate = useNavigate();
  const [session, setSession] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("safety-session")); } catch { return null; }
  });
  const [registeredUsername, setRegisteredUsername] = useState("");
  const [toast, setToast] = useState("");
  const notify = (message) => { setToast(message); window.clearTimeout(window.__toast); window.__toast = window.setTimeout(() => setToast(""), 2600); };
  const login = (nextSession) => {
    if (nextSession.role !== "admin") {
      apiRequest("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${nextSession.token}` } }).catch(() => {});
      notify("작업자 서비스는 모바일 앱을 이용해 주세요.");
      return;
    }
    sessionStorage.setItem("safety-session", JSON.stringify(nextSession));
    setSession(nextSession);
    navigate("/admin/dashboard", { replace: true });
  };
  const logout = async () => {
    try { await apiRequest("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${session.token}` } }); } catch { /* local logout still proceeds */ }
    sessionStorage.removeItem("safety-session");
    setSession(null);
    navigate("/login", { replace: true });
  };
  const registered = username => { setRegisteredUsername(username); navigate("/login", { replace: true }); notify("회원가입이 완료되었습니다. 로그인해 주세요."); };
  const homePath = session ? "/admin/dashboard" : "/login";
  const canUseAdmin = session && (session.role === "admin" || session.roles?.some(role => role === "ADMIN" || role === "SAFETY_MANAGER"));
  return <><Routes>
    <Route path="/login" element={session ? <Navigate to={homePath} replace/> : <Login initialUsername={registeredUsername} onRegister={() => navigate("/register")} onLogin={login} notify={notify} />}/>
    <Route path="/register" element={session ? <Navigate to={homePath} replace/> : <Register onBack={() => navigate("/login")} onRegistered={registered} notify={notify} />}/>
    <Route path="/admin/:page" element={canUseAdmin ? <Dashboard area="admin" session={session} onLogout={logout} notify={notify}/> : <Navigate to={homePath} replace/>}/>
    <Route path="*" element={<Navigate to={homePath} replace/>}/>
  </Routes>
    {toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}
  </>;
}

export default App;
