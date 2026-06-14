"use client";

import { useEffect, useState } from "react";
import { Lock, RefreshCw, MessageSquare, LogOut } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "finvox_admin_token";

export default function AdminFeedbackPage() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  // On first load, see if we already have a saved token and try it.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(TOKEN_KEY);
      if (saved) {
        setToken(saved);
        load(saved);
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load(t) {
    setLoading(true);
    setErr(null);
    try {
      const r = await fetch(`${API}/api/admin/feedback`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (r.status === 401 || r.status === 403) {
        setAuthed(false);
        try {
          localStorage.removeItem(TOKEN_KEY);
        } catch {}
        throw new Error("Invalid token. Check your ADMIN_TOKEN env var.");
      }
      if (!r.ok) throw new Error("Could not load feedback.");
      const data = await r.json();
      setItems(data.items || []);
      setCount(data.count || 0);
      setAuthed(true);
      try {
        localStorage.setItem(TOKEN_KEY, t);
      } catch {}
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  function submitLogin(e) {
    e.preventDefault();
    if (!token.trim()) return;
    load(token.trim());
  }

  function signOut() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {}
    setToken("");
    setItems([]);
    setCount(0);
    setAuthed(false);
  }

  if (!authed) {
    return (
      <div className="admin-login-wrap">
        <div className="admin-login-card">
          <div className="admin-icon">
            <Lock size={22} />
          </div>
          <h1>Finvox admin</h1>
          <p>Enter the admin token to view collected feedback.</p>
          <form onSubmit={submitLogin}>
            <input
              type="password"
              className="admin-input"
              placeholder="Admin token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoFocus
              required
            />
            {err && <p className="admin-error">{err}</p>}
            <button className="admin-btn" type="submit" disabled={loading}>
              {loading ? "Checking..." : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-wrap">
      <header className="admin-top">
        <div>
          <h1>
            <MessageSquare size={20} /> User feedback
          </h1>
          <p className="admin-sub">
            {count} {count === 1 ? "entry" : "entries"} collected
          </p>
        </div>
        <div className="admin-actions">
          <button
            className="admin-btn-ghost"
            onClick={() => load(token)}
            disabled={loading}
          >
            <RefreshCw size={14} /> {loading ? "Refreshing..." : "Refresh"}
          </button>
          <button className="admin-btn-ghost" onClick={signOut}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </header>

      {err && <p className="admin-error">{err}</p>}

      {items.length === 0 ? (
        <div className="admin-empty">
          <p>No feedback yet. Once visitors send something, it shows up here.</p>
        </div>
      ) : (
        <div className="admin-list">
          {items.map((f) => (
            <article key={f.id} className="admin-item">
              <div className="admin-item-head">
                <span className="admin-meta">
                  {new Date(f.created_at).toLocaleString("en-NG", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                {f.page && <span className="admin-tag">{f.page}</span>}
              </div>
              <p className="admin-message">{f.message}</p>
              {f.user_agent && (
                <p className="admin-ua" title={f.user_agent}>
                  {f.user_agent.slice(0, 90)}
                  {f.user_agent.length > 90 ? "..." : ""}
                </p>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
