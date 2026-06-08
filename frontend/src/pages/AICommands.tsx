import React, { useEffect, useState } from "react";
import { apiRequest } from "../api";
import type { AICommand, AICommandListResponse } from "../types";
import {
  Cpu,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Sparkles,
} from "lucide-react";

export const AICommands: React.FC = () => {
  const [commands, setCommands] = useState<AICommand[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState("");
  const [commandType, setCommandType] = useState("");
  const [userIdFilter, setUserIdFilter] = useState("");
  const [page, setPage] = useState(1);
  const limit = 10;

  // Selected Log for details
  const [selectedCommand, setSelectedCommand] = useState<AICommand | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      let queryParams = `?skip=${skip}&limit=${limit}`;
      if (statusFilter) queryParams += `&status=${statusFilter}`;
      if (commandType) queryParams += `&command_type=${commandType}`;
      if (userIdFilter) queryParams += `&user_id=${userIdFilter}`;

      const data = await apiRequest<AICommandListResponse>(`/system/ai/commands${queryParams}`);
      setCommands(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to fetch AI logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, statusFilter, commandType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "success":
      case "completed":
        return <span className="badge badge-success"><CheckCircle2 size={12} /> Bajarildi</span>;
      case "failed":
      case "error":
        return <span className="badge badge-danger"><XCircle size={12} /> Xato</span>;
      default:
        return <span className="badge badge-warning"><Clock size={12} /> Bajarilmoqda</span>;
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="ai-logs-page">
      {/* FILTER BAR */}
      <div className="filter-header glass-card">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <Search size={18} className="search-icon" />
          <input
            type="number"
            placeholder="Foydalanuvchi Telegram ID si bo'yicha qidirish..."
            className="glass-input search-input"
            value={userIdFilter}
            onChange={(e) => setUserIdFilter(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">Qidirish</button>
        </form>

        <div className="filters-row">
          <div className="filter-item">
            <Filter size={14} />
            <select className="glass-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">Barcha Statuslar</option>
              <option value="success">Success (Muvaffaqiyatli)</option>
              <option value="failed">Failed (Xatolik)</option>
              <option value="pending">Pending (Kutilmoqda)</option>
            </select>
          </div>

          <div className="filter-item">
            <Filter size={14} />
            <select className="glass-select" value={commandType} onChange={(e) => { setCommandType(e.target.value); setPage(1); }}>
              <option value="">Barcha AI Buyruqlar</option>
              <option value="find_order">Buyurtma qidirish (find_order)</option>
              <option value="track_order">Kuzatish (track_order)</option>
              <option value="cancel_order">Bekor qilish (cancel_order)</option>
              <option value="get_rating">Reytingni olish (get_rating)</option>
              <option value="get_history">Tarixni olish (get_history)</option>
              <option value="contact_support">Qo'llab-quvvatlash (contact_support)</option>
              <option value="custom">Boshqa (custom)</option>
            </select>
          </div>
        </div>
      </div>

      {/* LOGS TABLE */}
      <div className="logs-table-card glass-card">
        {loading ? (
          <div className="table-loader">
            <div className="spinner"></div>
            <p>AI loglari yuklanmoqda...</p>
          </div>
        ) : commands.length > 0 ? (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>User ID</th>
                  <th>Buyruq Turi</th>
                  <th>Kiritilgan matn (Raw Input)</th>
                  <th>Status</th>
                  <th>Kuni / Vaqti</th>
                  <th>Tafsilotlar</th>
                </tr>
              </thead>
              <tbody>
                {commands.map((cmd) => (
                  <tr key={cmd.id}>
                    <td>
                      <span className="log-id-badge">#{cmd.id}</span>
                    </td>
                    <td>
                      <span className="user-ref-badge">
                        <Sparkles size={11} /> {cmd.user_id || "Bot"}
                      </span>
                    </td>
                    <td>
                      <span className="command-type-lbl">{cmd.command_type}</span>
                    </td>
                    <td className="raw-input-cell">
                      <span className="raw-text-preview" title={cmd.raw_input || ""}>
                        {cmd.raw_input || <span className="text-muted">Audio / File</span>}
                      </span>
                    </td>
                    <td>{getStatusBadge(cmd.status)}</td>
                    <td>{new Date(cmd.created_at).toLocaleString()}</td>
                    <td>
                      <button className="btn btn-secondary btn-icon" onClick={() => setSelectedCommand(cmd)}>
                        <Eye size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-table">Hech qanday AI buyrug'i topilmadi.</div>
        )}

        {/* PAGINATION */}
        {totalPages > 1 && (
          <div className="table-footer">
            <span className="showing-text">
              Jami <b>{total}</b> tadan {((page - 1) * limit) + 1}-{Math.min(page * limit, total)} ko'rsatilmoqda
            </span>
            <div className="pagination">
              <button className="btn btn-secondary btn-icon" onClick={() => setPage(p => Math.max(p - 1, 1))} disabled={page === 1}>
                <ChevronLeft size={16} />
              </button>
              <span className="page-indicator">Sahifa {page} / {totalPages}</span>
              <button className="btn btn-secondary btn-icon" onClick={() => setPage(p => Math.min(p + 1, totalPages))} disabled={page === totalPages}>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* INSPECTOR MODAL */}
      {selectedCommand && (
        <div className="modal-backdrop">
          <div className="glass-card modal-content animate-slide-in inspector-modal">
            <div className="modal-header">
              <h3><Cpu size={18} /> AI So'rov Inspektori #{selectedCommand.id}</h3>
              <button className="close-btn" onClick={() => setSelectedCommand(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body inspector-modal-body">
              <div className="inspector-top-stats">
                <div className="stat-pill">
                  <span>Telegram User ID</span>
                  <p>{selectedCommand.user_id || "System"}</p>
                </div>
                <div className="stat-pill">
                  <span>Message ID</span>
                  <p>{selectedCommand.message_id || "N/A"}</p>
                </div>
                <div className="stat-pill">
                  <span>Sanasi</span>
                  <p>{new Date(selectedCommand.created_at).toLocaleString()}</p>
                </div>
              </div>

              {/* Raw Input Box */}
              <div className="code-block-wrap">
                <h5><MessageSquare size={13} /> Foydalanuvchi Matni (Raw Input):</h5>
                <div className="raw-text-box">
                  {selectedCommand.raw_input || "(Matn yo'q)"}
                </div>
              </div>

              {/* Parameters Box */}
              <div className="code-block-wrap">
                <h5>AI Tahlil Qilgan Parametrlar (Parameters):</h5>
                <pre className="json-pre">
                  {JSON.stringify(selectedCommand.parameters || {}, null, 2)}
                </pre>
              </div>

              {/* Execution Result or Error */}
              {selectedCommand.status === "failed" || selectedCommand.error_msg ? (
                <div className="code-block-wrap error-wrap">
                  <h5 className="text-danger">Xatolik Xabari (Error Message):</h5>
                  <div className="error-message-box">
                    {selectedCommand.error_msg || "Noma'lum xatolik yuz berdi."}
                  </div>
                </div>
              ) : (
                <div className="code-block-wrap success-wrap">
                  <h5 className="text-success">Natija (Result):</h5>
                  <pre className="json-pre">
                    {JSON.stringify(selectedCommand.result || {}, null, 2)}
                  </pre>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setSelectedCommand(null)}>
                Yopish
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .ai-logs-page {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .log-id-badge {
          background: rgba(255, 255, 255, 0.04);
          border: var(--glass-border);
          padding: 4px 8px;
          border-radius: var(--border-radius-sm);
          font-size: 12px;
          font-family: monospace;
          color: var(--text-secondary);
        }

        .user-ref-badge {
          background: rgba(0, 210, 255, 0.05);
          border: 1px solid rgba(0, 210, 255, 0.15);
          color: #80d8ff;
          padding: 4px 8px;
          border-radius: var(--border-radius-sm);
          font-size: 12px;
          font-family: monospace;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }

        .command-type-lbl {
          font-weight: 600;
          font-family: monospace;
          color: var(--accent-secondary);
          background: rgba(0, 210, 255, 0.05);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 13px;
        }

        .raw-input-cell {
          max-width: 250px;
        }

        .raw-text-preview {
          display: block;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          font-size: 13px;
        }

        /* Inspector Modal */
        .inspector-modal {
          max-width: 650px;
        }

        .inspector-modal-body {
          max-height: 70vh;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .inspector-top-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          background: rgba(0, 0, 0, 0.15);
          padding: 12px;
          border-radius: var(--border-radius);
          border: var(--glass-border);
        }

        .code-block-wrap {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .code-block-wrap h5 {
          font-size: 12px;
          font-weight: 700;
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .raw-text-box {
          background: rgba(255, 255, 255, 0.02);
          border: var(--glass-border);
          padding: 12px 16px;
          border-radius: var(--border-radius);
          font-size: 14px;
          font-style: italic;
          color: var(--text-primary);
        }

        .json-pre {
          background: #0d0e14;
          border: var(--glass-border);
          padding: 16px;
          border-radius: var(--border-radius);
          font-family: monospace;
          font-size: 12px;
          color: #a8ffb2;
          overflow-x: auto;
          max-height: 180px;
        }

        .error-message-box {
          background: rgba(255, 23, 68, 0.05);
          border: 1px solid rgba(255, 23, 68, 0.2);
          color: #ff8a80;
          padding: 16px;
          border-radius: var(--border-radius);
          font-family: monospace;
          font-size: 12px;
        }
      `}</style>
    </div>
  );
};
