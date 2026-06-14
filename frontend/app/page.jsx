"use client";

import { useEffect, useState } from "react";
import {
  Mic,
  NotebookPen,
  BarChart3,
  ShieldCheck,
  Languages,
  ArrowRight,
  MessageCircle,
  Lock,
  CheckCircle2,
  LayoutDashboard,
} from "lucide-react";
import FeedbackPopup from "./FeedbackPopup";

const WA_NUMBER = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || "15551234567";
const WA_LINK = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent("Hi Finvox!")}`;

export default function Home() {
  // Returning users (who have opened their ledger before) see their
  // dashboard instead of "Get started".
  const [dashToken, setDashToken] = useState(null);
  useEffect(() => {
    try {
      setDashToken(localStorage.getItem("finvox_token"));
    } catch {}
  }, []);
  const dashLink = dashToken ? `/ledger/${dashToken}` : null;

  return (
    <>
      <header className="container nav">
        <a className="logo" href="/">
          <span className="logo-mark"><Mic size={16} /></span>
          Finvox
        </a>
        {dashLink ? (
          <a className="nav-cta" href={dashLink}>
            <LayoutDashboard size={16} />
            My dashboard
          </a>
        ) : (
          <a className="nav-cta" href={WA_LINK}>
            <MessageCircle size={16} />
            Open WhatsApp
          </a>
        )}
      </header>

      <main>
        <section className="container hero">
          <div>
            <h1>
              Talk your sales.<br />
              <span className="accent">Finvox</span> keeps the books.
            </h1>
            <p className="sub">
              The bookkeeping assistant for Nigerian traders. Send a WhatsApp
              voice note in Pidgin, Hausa, Yoruba, Igbo or English and get a
              proper ledger, daily profit summaries, and a record of your
              business that banks can take seriously.
            </p>
            {dashLink ? (
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <a className="btn" href={dashLink}>
                  <LayoutDashboard size={18} />
                  Open my dashboard
                </a>
                <a className="btn ghost" href={WA_LINK}>
                  <MessageCircle size={17} />
                  Record on WhatsApp
                </a>
              </div>
            ) : (
              <a className="btn" href={WA_LINK}>
                Get started on WhatsApp
                <ArrowRight size={18} />
              </a>
            )}
            <p className="hero-note">
              <CheckCircle2 size={15} />
              {dashLink
                ? "Welcome back. Your books are waiting."
                : "Free. No app to download. Works on any phone with WhatsApp."}
            </p>
          </div>

          <div className="phone" aria-hidden="true">
            <div className="phone-screen">
              <div className="phone-top">
                <span className="avatar">F</span>
                Finvox
              </div>
              <div className="phone-body">
                <div className="msg out">
                  <span className="voice-row">
                    <Mic size={14} />
                    <span className="voice-bar" />
                    0:07
                  </span>
                  <time>9:14</time>
                </div>
                <div className="msg in">
                  {`Recorded:
Sale: crates of eggs, 5 x ₦3,000 = ₦15,000 (cash)

Today so far: sales ₦15,000 | expenses ₦0 | profit ₦15,000`}
                  <time>9:14</time>
                </div>
                <div className="msg out">
                  how my market today?
                  <time>18:02</time>
                </div>
                <div className="msg in">
                  {`Your summary for Today
Sales: ₦47,500
Expenses: ₦31,200
Profit: ₦16,300
Best seller: Pepper`}
                  <time>18:02</time>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="block alt">
          <div className="container">
            <div className="block-head">
              <p className="eyebrow">Why Finvox</p>
              <h2>Built for the market, not the office</h2>
              <p>
                Most bookkeeping apps assume forms, English and patience.
                Finvox assumes you are busy selling.
              </p>
            </div>
            <div className="grid">
              <div className="feature">
                <div className="ficon"><Mic size={20} /></div>
                <h3>Voice first</h3>
                <p>No forms, no typing. Talk the way you talk in the market and Finvox writes it down properly.</p>
              </div>
              <div className="feature">
                <div className="ficon"><Languages size={20} /></div>
                <h3>Your language</h3>
                <p>Pidgin, Hausa, Yoruba, Igbo or English. Finvox understands them all, spoken or typed.</p>
              </div>
              <div className="feature">
                <div className="ficon"><NotebookPen size={20} /></div>
                <h3>A real ledger</h3>
                <p>Every sale and expense organised like a bank statement, with payment mode, time and running balance.</p>
              </div>
              <div className="feature">
                <div className="ficon"><BarChart3 size={20} /></div>
                <h3>Daily summaries</h3>
                <p>Ask &quot;how my market today?&quot; and know your sales, expenses and profit in seconds.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="block">
          <div className="container">
            <div className="block-head">
              <p className="eyebrow">How it works</p>
              <h2>From voice note to bank statement</h2>
            </div>
            <div className="steps">
              <div className="step-card">
                <h3>Message Finvox</h3>
                <p>Your account and personal ledger are created automatically on your first WhatsApp message.</p>
              </div>
              <div className="step-card">
                <h3>Talk your transactions</h3>
                <p>&quot;I sell 3 bags of rice 15k, customer pay by transfer.&quot; Text or voice, one item or many.</p>
              </div>
              <div className="step-card">
                <h3>Get your statement</h3>
                <p>Finvox sends a private link to your full ledger. Filter it, export it to CSV or PDF, install it as an app.</p>
              </div>
              <div className="step-card">
                <h3>Build your record</h3>
                <p>Consistent records become proof of income you can show a lender when you need capital to grow.</p>
              </div>
            </div>

            <div style={{ marginTop: 40 }}>
              <div className="trust">
                <ShieldCheck size={26} />
                <div>
                  <h3>Private by design</h3>
                  <p>
                    Voice notes are processed and destroyed immediately. Only the
                    written transaction survives, and your ledger link belongs to
                    you alone. We never sell your data.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="final-cta container">
          <h2>Your first entry takes ten seconds</h2>
          <p>Send one message. Finvox does the rest.</p>
          <a className="btn" href={dashLink || WA_LINK}>
            {dashLink ? "Open my dashboard" : "Start free on WhatsApp"}
            <ArrowRight size={18} />
          </a>
        </section>
      </main>

      <footer>
        <div className="container" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span>Finvox. Built for the OPay National Innovation Challenge 2026.</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <Lock size={13} /> Made in Nigeria
          </span>
        </div>
      </footer>

      <FeedbackPopup />
    </>
  );
}
