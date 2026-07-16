import React, { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import Login from "./pages/auth/Login";
import Dashboard from "./components/layout/Dashboard";

function App() {
  const [session, setSession] = useState(null);
  const [toast, setToast] = useState("");
  const notify = (message) => { setToast(message); window.clearTimeout(window.__toast); window.__toast = window.setTimeout(() => setToast(""), 2600); };
  return <>{session ? <Dashboard session={session} onLogout={() => setSession(null)} notify={notify} /> : <Login onLogin={setSession} notify={notify} />}{toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}</>;
}

export default App;
