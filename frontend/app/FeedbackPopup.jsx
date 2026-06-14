"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, X, Send } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const STORAGE_KEY = "finvox_feedback_done";
const DELAY_MS = 20_000;

/**
 * Shows a feedback popup 10 seconds after the visitor's first interaction
 * (any mousemove / scroll / key / touch). Only shown once per browser:
 * once submitted or dismissed, we set a localStorage flag and never show again.
 */
export default function FeedbackPopup() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    // Skip if already shown for this browser.
    try {
      if (localStorage.getItem(STORAGE_KEY)) return;
    } catch {
      return;
    }

    const events = ["mousemove", "scroll", "keydown", "touchstart", "click"];
    const onInteract = () => {
      // Only start the timer once, on the very first interaction.
      events.forEach((e) => window.removeEventListener(e, onInteract));
      timerRef.current = setTimeout(() => setOpen(true), DELAY_MS);
    };
    events.forEach((e) =>
      window.addEventListener(e, onInteract, { passive: true, once: false })
    );

    return () => {
      events.forEach((e) => window.removeEventListener(e, onInteract));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function markDone() {
    try {
      localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    } catch {}
  }

  function close() {
    markDone();
    setOpen(false);
  }

  async function submit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          page: typeof window !== "undefined" ? window.location.pathname : null,
        }),
      });
      if (!r.ok) throw new Error("Could not send feedback. Please try again.");
      setDone(true);
      markDone();
      // Auto-close after a moment so the user sees the thanks state.
      setTimeout(() => setOpen(false), 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fb-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="fb-title"
      onClick={(e) => {
        // Click outside the card closes the popup.
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="fb-card">
        <button
          type="button"
          className="fb-close"
          aria-label="Close feedback"
          onClick={close}
        >
          <X size={18} />
        </button>

        {done ? (
          <div className="fb-thanks">
            <div className="fb-icon">
              <MessageSquare size={22} />
            </div>
            <h3>Thank you!</h3>
            <p>Your feedback helps us make Finvox better.</p>
          </div>
        ) : (
          <>
            <div className="fb-icon">
              <MessageSquare size={22} />
            </div>
            <h3 id="fb-title">Tell us what you think</h3>
            <p className="fb-sub">
              What works, what does not, what you wish Finvox could do. One line is
              fine.
            </p>

            <form onSubmit={submit}>
              <textarea
                className="fb-textarea"
                placeholder="Your feedback..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={4000}
                rows={4}
                autoFocus
                required
              />
              {error && <p className="fb-error">{error}</p>}
              <div className="fb-actions">
                <button
                  type="button"
                  className="fb-btn-ghost"
                  onClick={close}
                  disabled={sending}
                >
                  Not now
                </button>
                <button
                  type="submit"
                  className="fb-btn"
                  disabled={sending || !text.trim()}
                >
                  <Send size={15} />
                  {sending ? "Sending..." : "Send"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
