"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  Mic,
  MessageCircle,
  Download,
  Printer,
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
  Banknote,
  ArrowLeftRight,
  CreditCard,
  HandCoins,
  Lock,
  CalendarClock,
  List,
  FileText,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const naira = (n) =>
  "₦" + Number(n).toLocaleString("en-NG", { maximumFractionDigits: 2 });

const MODES = {
  cash: { label: "Cash", Icon: Banknote },
  transfer: { label: "Transfer", Icon: ArrowLeftRight },
  pos: { label: "POS", Icon: CreditCard },
  owed: { label: "Owed", Icon: HandCoins },
};

const PERIODS = [
  { key: "today", label: "Today", days: 0 },
  { key: "7d", label: "7 days", days: 7 },
  { key: "30d", label: "30 days", days: 30 },
  { key: "all", label: "All time", days: null },
];

function fmtStamp(iso) {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString("en-NG", { day: "2-digit", month: "short", year: "numeric" }),
    time: d.toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" }),
  };
}

const iso = (d) => d.toISOString().slice(0, 10);

export default function LedgerPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [tab, setTab] = useState("transactions");
  const [period, setPeriod] = useState("all");
  const [flow, setFlow] = useState("all");

  // statements tab state
  const [range, setRange] = useState({ start: "", end: "" });
  const [stmt, setStmt] = useState(null);
  const [stmtLoading, setStmtLoading] = useState(false);
  const [stmtErr, setStmtErr] = useState(null);

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/ledger/${token}`)
      .then((r) => {
        if (!r.ok) {
          if (r.status === 404) {
            try { localStorage.removeItem("finvox_token"); } catch {}
            throw new Error("Ledger not found");
          }
          throw new Error("Could not load your ledger");
        }
        return r.json();
      })
      .then((d) => {
        setData(d);
        // Remember this user so the home page shows "My dashboard".
        try { localStorage.setItem("finvox_token", token); } catch {}
      })
      .catch((e) => setErr(e.message));
  }, [token]);

  const rows = useMemo(() => {
    if (!data) return [];
    const asc = [...data.transactions].sort((a, b) => a.id - b.id);
    let bal = 0;
    const withBal = asc.map((t) => {
      bal += t.type === "sale" ? t.amount : -t.amount;
      return { ...t, balance: bal };
    });
    let out = withBal;
    const p = PERIODS.find((x) => x.key === period);
    if (p && p.days !== null) {
      const cutoff = new Date();
      cutoff.setHours(0, 0, 0, 0);
      cutoff.setDate(cutoff.getDate() - p.days);
      out = out.filter((t) => new Date(t.timestamp) >= cutoff);
    }
    if (flow === "in") out = out.filter((t) => t.type === "sale");
    if (flow === "out") out = out.filter((t) => t.type !== "sale");
    return out.reverse();
  }, [data, period, flow]);

  const filteredTotals = useMemo(() => {
    let sales = 0, expenses = 0;
    for (const t of rows) {
      if (t.type === "sale") sales += t.amount;
      else expenses += t.amount;
    }
    return { sales, expenses, profit: sales - expenses };
  }, [rows]);

  function exportCSV() {
    const head = ["Date", "Time", "Description", "Customer/Supplier", "Quantity", "Unit Price", "Payment Mode", "Debit (NGN)", "Credit (NGN)", "Balance (NGN)", "Source"];
    const lines = [head.join(",")];
    for (const t of [...rows].reverse()) {
      const s = fmtStamp(t.timestamp);
      const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      lines.push([
        esc(s.date), esc(s.time), esc(t.item), esc(t.counterparty ?? ""),
        t.quantity ?? "", t.unit_price ?? "",
        MODES[t.payment_method]?.label ?? "Cash",
        t.type !== "sale" ? t.amount : "",
        t.type === "sale" ? t.amount : "",
        t.balance,
        t.source,
      ].join(","));
    }
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `finvox-statement-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function preset(kind) {
    const now = new Date();
    if (kind === "month") {
      setRange({ start: iso(new Date(now.getFullYear(), now.getMonth(), 1)), end: iso(now) });
    } else if (kind === "lastMonth") {
      setRange({
        start: iso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
        end: iso(new Date(now.getFullYear(), now.getMonth(), 0)),
      });
    } else if (kind === "year") {
      setRange({ start: iso(new Date(now.getFullYear(), 0, 1)), end: iso(now) });
    } else {
      setRange({ start: "", end: "" });
    }
  }

  async function generateStatements() {
    setStmtLoading(true);
    setStmtErr(null);
    try {
      const qs = new URLSearchParams();
      if (range.start) qs.set("start", range.start);
      if (range.end) qs.set("end", range.end);
      const r = await fetch(`${API}/api/ledger/${token}/statements?${qs}`);
      if (!r.ok) throw new Error("Could not generate statements for that period");
      setStmt(await r.json());
    } catch (e) {
      setStmtErr(e.message);
    } finally {
      setStmtLoading(false);
    }
  }

  if (err)
    return (
      <div className="center">
        <h2 style={{ fontFamily: "var(--font-display)", marginBottom: 8 }}>{err}</h2>
        <p>Check the link Finvox sent you on WhatsApp.</p>
      </div>
    );

  if (!data)
    return (
      <div className="ledger-wrap">
        <div className="skel" style={{ height: 34, width: 220, margin: "18px 0" }} />
        <div className="cards">
          {[0, 1, 2, 3].map((i) => <div key={i} className="skel" style={{ height: 86 }} />)}
        </div>
        <div className="skel" style={{ height: 320 }} />
      </div>
    );

  const { user, today, debts } = data;
  const is = stmt?.income_statement;
  const cf = stmt?.cash_flow;
  const bs = stmt?.balance_sheet;

  return (
    <div className="ledger-wrap">
      <header className="ledger-top">
        <div>
          <a className="logo" href="/">
            <span className="logo-mark"><Mic size={15} /></span>
            Finvox
          </a>
          <h1 style={{ marginTop: 10 }}>{user.name ? `${user.name}'s Books` : "My Books"}</h1>
          <div className="meta-row">
            <span className="chip"><MessageCircle size={13} /> WhatsApp {user.phone_masked}</span>
            <span className="chip"><CalendarClock size={13} /> Member since {user.member_since}</span>
          </div>
        </div>
        {tab === "transactions" && (
          <div className="actions">
            <button className="act-btn" onClick={exportCSV}>
              <Download size={15} /> CSV
            </button>
            <button className="act-btn" onClick={() => window.print()}>
              <Printer size={15} /> PDF
            </button>
          </div>
        )}
      </header>

      <div className="tabs">
        <button className={`tab ${tab === "transactions" ? "on" : ""}`} onClick={() => setTab("transactions")}>
          <List size={15} /> Transactions
        </button>
        <button className={`tab ${tab === "statements" ? "on" : ""}`} onClick={() => setTab("statements")}>
          <FileText size={15} /> Financial statements
        </button>
      </div>

      {tab === "transactions" && (
        <>
          <div className="cards">
            <div className="card">
              <div className="label"><TrendingUp size={13} /> Today, sales</div>
              <div className="value pos">{naira(today.sales)}</div>
            </div>
            <div className="card">
              <div className="label"><TrendingDown size={13} /> Today, expenses</div>
              <div className="value neg">{naira(today.expenses)}</div>
            </div>
            <div className="card">
              <div className="label"><Wallet size={13} /> Today, profit</div>
              <div className={`value ${today.profit >= 0 ? "pos" : "neg"}`}>{naira(today.profit)}</div>
            </div>
            <div className="card">
              <div className="label"><PiggyBank size={13} /> Profit, filtered view</div>
              <div className={`value ${filteredTotals.profit >= 0 ? "pos" : "neg"}`}>{naira(filteredTotals.profit)}</div>
            </div>
            <div className="card">
              <div className="label"><HandCoins size={13} /> Owed to me</div>
              <div className="value pos">{naira(debts?.owed_to_me ?? 0)}</div>
            </div>
            <div className="card">
              <div className="label"><HandCoins size={13} /> I owe</div>
              <div className="value neg">{naira(debts?.i_owe ?? 0)}</div>
            </div>
          </div>

          <div className="filters">
            {PERIODS.map((p) => (
              <button key={p.key} className={`fchip ${period === p.key ? "on" : ""}`} onClick={() => setPeriod(p.key)}>
                {p.label}
              </button>
            ))}
            <span className="fdivider" />
            {[["all", "All"], ["in", "Money in"], ["out", "Money out"]].map(([k, label]) => (
              <button key={k} className={`fchip ${flow === k ? "on" : ""}`} onClick={() => setFlow(k)}>
                {label}
              </button>
            ))}
          </div>

          {rows.length === 0 ? (
            <div className="stmt-card">
              <div className="empty">
                <h3>No transactions in this view</h3>
                <p>Send Finvox a message like &quot;I sell 5 crates of egg, 3000 each&quot; and it will appear here.</p>
              </div>
            </div>
          ) : (
            <div className="stmt-card">
              <table className="stmt">
                <thead>
                  <tr>
                    <th>Date &amp; Time</th>
                    <th>Description</th>
                    <th>Mode</th>
                    <th style={{ textAlign: "right" }}>Debit</th>
                    <th style={{ textAlign: "right" }}>Credit</th>
                    <th style={{ textAlign: "right" }}>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((t) => {
                    const s = fmtStamp(t.timestamp);
                    const m = MODES[t.payment_method] || MODES.cash;
                    return (
                      <tr key={t.id}>
                        <td data-l="Date" className="tstamp">
                          <span className="d">{s.date}</span>
                          <span className="t">{s.time}</span>
                        </td>
                        <td data-l="Description" className="desc">
                          {t.item}
                          {t.quantity && t.unit_price ? ` (${t.quantity} x ${naira(t.unit_price)})` : ""}
                          {t.counterparty ? <span className="cp"> · {t.counterparty}</span> : null}
                          <span className="src-tag">
                            {t.source === "voice" ? <Mic size={11} /> : <MessageCircle size={11} />}
                            {t.source}
                          </span>
                        </td>
                        <td data-l="Mode">
                          <span className={`mode ${t.payment_method}`}>
                            <m.Icon size={12} />
                            {m.label}
                          </span>
                        </td>
                        <td data-l="Debit" className="amt debit">
                          {t.type !== "sale" ? naira(t.amount) : ""}
                        </td>
                        <td data-l="Credit" className="amt credit">
                          {t.type === "sale" ? naira(t.amount) : ""}
                        </td>
                        <td data-l="Balance" className="amt balance">{naira(t.balance)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "statements" && (
        <>
          <div className="filters">
            <button className="fchip" onClick={() => preset("month")}>This month</button>
            <button className="fchip" onClick={() => preset("lastMonth")}>Last month</button>
            <button className="fchip" onClick={() => preset("year")}>This year</button>
            <button className="fchip" onClick={() => preset("all")}>All time</button>
            <span className="fdivider" />
            <input type="date" className="date-in" value={range.start}
                   onChange={(e) => setRange({ ...range, start: e.target.value })} />
            <span style={{ color: "var(--ink-soft)", fontSize: "0.85rem" }}>to</span>
            <input type="date" className="date-in" value={range.end}
                   onChange={(e) => setRange({ ...range, end: e.target.value })} />
            <button className="act-btn" style={{ borderColor: "var(--green)", background: "var(--green-tint)" }}
                    onClick={generateStatements} disabled={stmtLoading}>
              <FileText size={15} /> {stmtLoading ? "Preparing..." : "Generate"}
            </button>
          </div>

          {stmtErr && <p className="center" style={{ padding: 20 }}>{stmtErr}</p>}

          {!stmt && !stmtErr && (
            <div className="stmt-card">
              <div className="empty">
                <h3>Generate your financial statements</h3>
                <p>Pick a period above and press Generate. You will get an income statement, a cash flow statement and a balance sheet, ready to print or save as PDF.</p>
              </div>
            </div>
          )}

          {stmt && (
            <div className="fin-doc">
              <div className="fin-head">
                <div>
                  <h2>{stmt.business}</h2>
                  <p>Financial statements for {stmt.period.start} to {stmt.period.end}</p>
                  <p className="fin-sub">Prepared {stmt.prepared_on} from {stmt.transaction_count} recorded transactions · Finvox</p>
                </div>
                <button className="act-btn" onClick={() => window.print()}>
                  <Printer size={15} /> Print / PDF
                </button>
              </div>

              <section className="fin-section">
                <h3>Income Statement</h3>
                <table className="fin-table">
                  <tbody>
                    <tr className="fin-group"><td>Revenue</td><td /></tr>
                    {is.revenue_items.map((r) => (
                      <tr key={r.label}><td className="indent">{r.label}</td><td className="amt">{naira(r.amount)}</td></tr>
                    ))}
                    <tr className="fin-total"><td>Total revenue</td><td className="amt">{naira(is.revenue_total)}</td></tr>
                    {is.of_which_credit_sales > 0 && (
                      <tr><td className="indent fin-sub">of which credit sales (not yet paid)</td><td className="amt fin-sub">{naira(is.of_which_credit_sales)}</td></tr>
                    )}
                    <tr className="fin-group"><td>Cost of goods sold</td><td /></tr>
                    <tr><td className="indent">Opening inventory</td><td className="amt">{naira(is.cogs.opening_inventory)}</td></tr>
                    <tr><td className="indent">Stock purchases</td><td className="amt">{naira(is.cogs.stock_purchases)}</td></tr>
                    <tr><td className="indent">Less: closing inventory</td><td className="amt">({naira(is.cogs.closing_inventory)})</td></tr>
                    <tr className="fin-total"><td>Cost of goods sold</td><td className="amt">({naira(is.cogs.total)})</td></tr>
                    <tr className="fin-total"><td>Gross profit</td><td className="amt">{naira(is.gross_profit)}</td></tr>
                    <tr className="fin-group"><td>Operating expenses</td><td /></tr>
                    {is.expense_items.length === 0 && (
                      <tr><td className="indent">No operating expenses recorded</td><td className="amt">{naira(0)}</td></tr>
                    )}
                    {is.expense_items.map((r) => (
                      <tr key={r.label}><td className="indent">{r.label}</td><td className="amt">({naira(r.amount)})</td></tr>
                    ))}
                    <tr className="fin-total"><td>Total operating expenses</td><td className="amt">({naira(is.expense_total)})</td></tr>
                    <tr className="fin-grand"><td>Net profit</td><td className="amt">{naira(is.net_profit)}</td></tr>
                  </tbody>
                </table>
              </section>

              <section className="fin-section">
                <h3>Cash Flow Statement</h3>
                <table className="fin-table">
                  <tbody>
                    <tr><td>Opening cash</td><td className="amt">{naira(cf.opening_cash)}</td></tr>
                    <tr className="fin-group"><td>Cash received</td><td /></tr>
                    {cf.inflows.length === 0 && (
                      <tr><td className="indent">No cash received</td><td className="amt">{naira(0)}</td></tr>
                    )}
                    {cf.inflows.map((r) => (
                      <tr key={r.label}><td className="indent">{r.label}</td><td className="amt">{naira(r.amount)}</td></tr>
                    ))}
                    <tr className="fin-total"><td>Total cash in</td><td className="amt">{naira(cf.cash_in)}</td></tr>
                    <tr><td>Cash paid out</td><td className="amt">({naira(cf.cash_out)})</td></tr>
                    <tr className="fin-total"><td>Net cash flow</td><td className="amt">{naira(cf.net_cash_flow)}</td></tr>
                    <tr className="fin-grand"><td>Closing cash</td><td className="amt">{naira(cf.closing_cash)}</td></tr>
                  </tbody>
                </table>
              </section>

              <section className="fin-section">
                <h3>Balance Sheet <span className="fin-sub">as of {bs.as_of}</span></h3>
                <table className="fin-table">
                  <tbody>
                    <tr className="fin-group"><td>Assets</td><td /></tr>
                    <tr><td className="indent">Cash</td><td className="amt">{naira(bs.cash)}</td></tr>
                    <tr><td className="indent">Receivables (customers owe you)</td><td className="amt">{naira(bs.receivables)}</td></tr>
                    <tr><td className="indent">Inventory (stock on hand)</td><td className="amt">{naira(bs.inventory ?? 0)}</td></tr>
                    <tr className="fin-total"><td>Total assets</td><td className="amt">{naira(bs.total_assets)}</td></tr>
                    <tr className="fin-group"><td>Liabilities</td><td /></tr>
                    <tr><td className="indent">Payables (you owe suppliers)</td><td className="amt">{naira(bs.payables)}</td></tr>
                    <tr className="fin-total"><td>Total liabilities</td><td className="amt">{naira(bs.total_liabilities)}</td></tr>
                    <tr className="fin-grand"><td>Owner&apos;s equity</td><td className="amt">{naira(bs.equity)}</td></tr>
                  </tbody>
                </table>
              </section>

              <div className="fin-notes">
                {stmt.notes.map((n, i) => <p key={i}>{i + 1}. {n}</p>)}
              </div>
            </div>
          )}
        </>
      )}

      <p className="ledger-foot">
        <Lock size={13} />
        Keep this link private. Anyone who has it can view your books.
      </p>
    </div>
  );
}
