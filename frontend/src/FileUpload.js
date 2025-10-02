import React, { useState, useRef, useEffect } from "react";
import { uploadDocument } from "./api";
import "./FileUpload.css";
import Swal from "sweetalert2";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

function FileUpload() {
  const [file, setFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0); // ⏱ track elapsed time
  const messagesEndRef = useRef(null);
  const timerRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: `\n \n Uploaded file: ${file.name}` },
    ]);

    // Start timer
    setElapsed(0);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    setLoading(true);
    const start = performance.now();

    try {
      const data = await uploadDocument(file);
      const end = performance.now();
      const duration = ((end - start) / 1000).toFixed(2);

      // Stop timer
      clearInterval(timerRef.current);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          summary: data.summary,
          text: data.text,
          results: data.results,
          isTable: true,
          responseTime: duration,
        },
      ]);
    } catch (err) {
      clearInterval(timerRef.current);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Upload failed. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCalendar = async (row) => {
    try {
      const response = await fetch(`${API_BASE_URL}/calendar/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: row.event,
          description: row.obligation,
          start: row.event_date,
          end: row.obligation_date || row.event_date,
        }),
      });
      const data = await response.json();

      Swal.fire({
        title: "📅 Added to Calendar!",
        html: `<b>${data.event.title}</b> has been scheduled.`,
        icon: "success",
        confirmButtonText: "OK",
        background: "#f9f9f9",
        color: "#333",
      });
    } catch (error) {
      Swal.fire({
        title: "⚠️ Calendar Sync Failed",
        text: "Please try again.",
        icon: "error",
        confirmButtonText: "OK",
      });
    }
  };

  const handleNotify = async (row) => {
    try {
      const response = await fetch(`${API_BASE_URL}/notify/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `Reminder: ${row.obligation || row.event}`,
          channel: "email",
        }),
      });
      const data = await response.json();

      Swal.fire({
        title: "🔔 Notification Sent!",
        html: `Reminder for <b>${row.event}</b> was sent via <b>${data.channel}</b>.`,
        icon: "success",
        confirmButtonText: "Great!",
        background: "#f9f9f9",
        color: "#333",
      });
    } catch (error) {
      Swal.fire({
        title: "⚠️ Notification Failed",
        text: "Please try again.",
        icon: "error",
        confirmButtonText: "OK",
        background: "#fff5f5",
        color: "#b71c1c",
      });
    }
  };

  const handleShowDetails = (row) => {
    const parts = [];
    if (row.relative_rule) parts.push(`<div><b>Rule:</b> ${row.relative_rule}</div>`);
    if (row.rule_type) parts.push(`<div><b>Rule Type:</b> ${row.rule_type}</div>`);
    if (typeof row.business_days === "boolean") parts.push(`<div><b>Business Days:</b> ${row.business_days}</div>`);
    if (row.trigger_event) parts.push(`<div><b>Trigger Event:</b> ${row.trigger_event}</div>`);
    if (row.offset_days !== null && row.offset_days !== undefined) parts.push(`<div><b>Offset Days:</b> ${row.offset_days}</div>`);
    if (row.evidence_text) parts.push(`<hr/><div style="font-size:13px;"><b>Evidence:</b><br/><em>${row.evidence_text}</em></div>`);
    if (row.why) parts.push(`<div style="margin-top:6px;"><b>Why:</b> ${row.why}</div>`);

    Swal.fire({
      title: "Details",
      html: parts.join(""),
      icon: "info",
      confirmButtonText: "Close",
      background: "#f9f9f9",
      color: "#333",
    });
  };

  const getRowClass = (priority) => {
    switch (priority) {
      case "Overdue":
        return "row-overdue";
      case "High":
        return "row-high";
      case "Medium":
        return "row-normal";
      default:
        return "row-low";
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <h1 className="chat-title"> ⚖️ AI Legal Copilot</h1>

        <div className="instructions">
          <p>
            <b>
              Upload a legal PDF file, and AI Legal Copilot will extract key
              events, dates, and obligations.
            </b>
          </p>
          <p>
            <b>
              You can also set status, add deadlines to your calendar, send
              notifications, or prioritize upcoming obligations.
            </b>
          </p>
        </div>

        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className="assistant">
              {msg.isTable ? (
                <div>
                  {msg.summary && (
                    <div className="summary-block">
                      <h3>📄 Document Summary</h3>
                      <p>{msg.summary}</p>
                    </div>
                  )}

                  {msg.text && (
                    <div className="document-block">
                      <h3>📜 Original Document</h3>
                      <pre className="document-text">{msg.text}</pre>
                    </div>
                  )}

                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Priority</th>
                        <th>Event</th>
                        <th>Event Date</th>
                        <th>Obligation</th>
                        <th>Obligation Date</th>
                        <th>
                          Internal Obligation Due Date <br />
                          (Obligation Date - 1 Day)
                        </th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {msg.results.map((row, idx) => {
                        let internalDate = "-";
                        if (row.obligation_date) {
                          try {
                            const d = new Date(row.obligation_date);
                            d.setDate(d.getDate() - 1);
                            internalDate = d.toISOString().split("T")[0];
                          } catch {
                            internalDate = "-";
                          }
                        }

                        const priority = row.priority
                          ? row.priority.charAt(0).toUpperCase() +
                            row.priority.slice(1)
                          : "Low";

                        return (
                          <tr key={idx} className={getRowClass(row.priority)}>
                            <td>{priority}</td>
                            <td>{row.event}</td>
                            <td>{row.event_date || "-"}</td>
                            <td>{row.obligation || "-"}</td>
                            <td>{row.obligation_date || "-"}</td>
                            <td>{internalDate}</td>
                            <td>
                              <select
                                value={row.status || "Not Started"}
                                onChange={(e) => {
                                  const newStatus = e.target.value;
                                  setMessages((prev) =>
                                    prev.map((m, mi) =>
                                      m.isTable
                                        ? {
                                            ...m,
                                            results: m.results.map((r, ri) =>
                                              ri === idx
                                                ? { ...r, status: newStatus }
                                                : r
                                            ),
                                          }
                                        : m
                                    )
                                  );
                                }}
                              >
                                <option value="Not Started">Not Started</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Done">Done</option>
                              </select>
                            </td>
                            <td>
                              <div className="actions-container">
                                <button
                                  className="btn-action btn-calendar"
                                  title="Add to Calendar"
                                  onClick={() => handleAddToCalendar(row)}
                                >
                                  📅
                                </button>
                                <button
                                  className="btn-action btn-notify"
                                  title="Send Notification"
                                  onClick={() => handleNotify(row)}
                                >
                                  🔔
                                </button>
                              </div>
                            </td>

                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  <div className="response-meta">⏱ {msg.responseTime}s</div>
                </div>
              ) : (
                <pre>{msg.content}</pre>
              )}
            </div>
          ))}

          {/* Typing bubble with elapsed time */}
          {loading && (
            <div className="assistant typing-indicator">
              <span></span>
              <span></span>
              <span></span>
              <div className="elapsed-time">⏱ {elapsed}s</div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input">
          <input type="file" onChange={handleFileChange} />
          <button onClick={handleUpload} disabled={!file || loading}>
            Extract
          </button>
        </div>
      </div>
    </div>
  );
}

export default FileUpload;
