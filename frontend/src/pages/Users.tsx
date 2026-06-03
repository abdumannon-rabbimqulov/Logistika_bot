import React, { useEffect, useState } from "react";
import { apiRequest } from "../api";
import type { User, UserListResponse } from "../types";
import { UserRole } from "../types";
import {
  Search,
  Filter,
  UserX,
  UserCheck,
  Edit2,
  Trash2,
  X,
  ChevronLeft,
  ChevronRight,
  Shield,
  Phone,
  DollarSign,
  Globe,
  Calendar,
} from "lucide-react";

export const Users: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
  // Filtering & Pagination state
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<string>("");
  const [status, setStatus] = useState<string>(""); // "active", "banned"
  const [page, setPage] = useState(1);
  const limit = 10;

  // Selected User for Detail/Edit Modal
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState<UserRole | "">("");
  const [editActive, setEditActive] = useState(true);
  const [editBanned, setEditBanned] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [actionError, setActionError] = useState("");

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      let queryParams = `?skip=${skip}&limit=${limit}`;
      if (search) queryParams += `&search=${encodeURIComponent(search)}`;
      if (role) queryParams += `&role=${role}`;
      if (status === "banned") queryParams += `&is_banned=true`;
      if (status === "active") queryParams += `&is_banned=false`;

      const data = await apiRequest<UserListResponse>(`/system/users${queryParams}`);
      setUsers(data.items);
      setTotal(data.total);
    } catch (err: any) {
      console.error("Failed to load users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, role, status]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleOpenEditModal = (user: User) => {
    setSelectedUser(user);
    setEditName(user.full_name);
    setEditRole(user.role || "");
    setEditActive(user.is_active);
    setEditBanned(user.is_banned);
    setActionError("");
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;
    setIsSaving(true);
    setActionError("");
    try {
      const payload: any = {
        full_name: editName,
        role: editRole || null,
        is_active: editActive,
        is_banned: editBanned,
      };

      const updatedUser = await apiRequest<User>(`/system/users/${selectedUser.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      // Update local state list
      setUsers(users.map(u => u.id === selectedUser.id ? updatedUser : u));
      setSelectedUser(null);
    } catch (err: any) {
      setActionError(err.message || "Foydalanuvchi ma'lumotlarini tahrirlashda xatolik.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!window.confirm(`${user.full_name} akkauntini o'chirishga (deaktivatsiya) ishonchingiz komilmi?`)) return;
    try {
      await apiRequest(`/system/users/${user.id}`, {
        method: "DELETE",
      });
      // Refresh list
      fetchUsers();
    } catch (err: any) {
      alert(err.message || "Deaktivatsiya qilishda xatolik.");
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="users-page">
      {/* FILTER & SEARCH HEADER */}
      <div className="filter-header glass-card">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Ism, telefon raqam yoki telegram username bo'yicha qidirish..."
            className="glass-input search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">Qidirish</button>
        </form>

        <div className="filters-row">
          <div className="filter-item">
            <Filter size={14} />
            <select className="glass-select" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}>
              <option value="">Barcha Rollar</option>
              <option value={UserRole.ADMIN}>Adminlar</option>
              <option value={UserRole.DRIVER}>Haydovchilar</option>
              <option value={UserRole.CLIENT}>Mijozlar</option>
              <option value={UserRole.DISPATCHER}>Dispetcherlar</option>
            </select>
          </div>

          <div className="filter-item">
            <Filter size={14} />
            <select className="glass-select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              <option value="">Barcha Statuslar</option>
              <option value="active">Aktiv (Bloklanmagan)</option>
              <option value="banned">Bloklanganlar</option>
            </select>
          </div>
        </div>
      </div>

      {/* USERS LIST TABLE */}
      <div className="users-table-card glass-card">
        {loading ? (
          <div className="table-loader">
            <div className="spinner"></div>
            <p>Foydalanuvchilar ro'yxati yuklanmoqda...</p>
          </div>
        ) : users.length > 0 ? (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Telegram ID</th>
                  <th>F.I.SH</th>
                  <th>Telefon Raqam</th>
                  <th>Rol</th>
                  <th>Tizim Holati</th>
                  <th>Ro'yxatdan o'tdi</th>
                  <th>Amallar</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className={u.is_banned ? "row-banned" : ""}>
                    <td>
                      <span className="tg-id-badge">
                        <Shield size={12} /> {u.id}
                      </span>
                    </td>
                    <td>
                      <div className="user-name-cell">
                        <span className="user-fullname">{u.full_name}</span>
                        {u.username && <span className="user-username">@{u.username}</span>}
                      </div>
                    </td>
                    <td>{u.phone_number || <span className="text-muted">Kiritilmagan</span>}</td>
                    <td>
                      <span className={`badge ${u.role === UserRole.ADMIN ? "badge-primary" : u.role === UserRole.DRIVER ? "badge-success" : u.role === UserRole.DISPATCHER ? "badge-info" : "badge-neutral"}`}>
                        {u.role || "client"}
                      </span>
                    </td>
                    <td>
                      {u.is_banned ? (
                        <span className="badge badge-danger">Bloklangan</span>
                      ) : u.is_active ? (
                        <span className="badge badge-success">Faol</span>
                      ) : (
                        <span className="badge badge-neutral">Faol emas</span>
                      )}
                    </td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="table-actions">
                        <button className="btn btn-secondary btn-icon" title="Tahrirlash" onClick={() => handleOpenEditModal(u)}>
                          <Edit2 size={14} />
                        </button>
                        <button className="btn btn-secondary btn-icon text-danger" title="Akkauntni o'chirish" onClick={() => handleDeactivate(u)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-table">Foydalanuvchilar topilmadi.</div>
        )}

        {/* PAGINATION FOOTER */}
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

      {/* DETAIL & EDIT MODAL OVERLAY */}
      {selectedUser && (
        <div className="modal-backdrop">
          <div className="glass-card modal-content animate-slide-in user-modal">
            <div className="modal-header">
              <h3>Profil Moderatsiyasi</h3>
              <button className="close-btn" onClick={() => setSelectedUser(null)}>
                <X size={18} />
              </button>
            </div>
            
            {actionError && <div className="alert-message danger-alert">{actionError}</div>}

            <div className="modal-body user-modal-body">
              {/* Profile Card Header */}
              <div className="user-detail-header">
                <div className="avatar">
                  {selectedUser.full_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h4>{selectedUser.full_name}</h4>
                  <p className="tg-username-line">
                    {selectedUser.username ? `@${selectedUser.username}` : "Telegram Username yo'q"} (ID: {selectedUser.id})
                  </p>
                </div>
              </div>

              {/* Grid info stats */}
              <div className="user-meta-grid">
                <div className="meta-card">
                  <Phone size={14} />
                  <div>
                    <span>Telefon Raqami</span>
                    <p>{selectedUser.phone_number || "Kiritilmagan"}</p>
                  </div>
                </div>
                <div className="meta-card">
                  <DollarSign size={14} />
                  <div>
                    <span>Hisob Balansi</span>
                    <p>{Number(selectedUser.balance).toLocaleString()} UZS</p>
                  </div>
                </div>
                <div className="meta-card">
                  <Globe size={14} />
                  <div>
                    <span>Tizim Tili</span>
                    <p>{selectedUser.language.toUpperCase()}</p>
                  </div>
                </div>
                <div className="meta-card">
                  <Calendar size={14} />
                  <div>
                    <span>A'zo bo'ldi</span>
                    <p>{new Date(selectedUser.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </div>

              <div className="divider"></div>

              {/* Form editing sections */}
              <div className="edit-form-grid">
                <div className="form-group">
                  <label>To'liq Ism (F.I.SH):</label>
                  <input
                    type="text"
                    className="glass-input"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Tizimdagi Roli:</label>
                  <select
                    className="glass-select"
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as UserRole)}
                  >
                    <option value="">Tanlang (Mijoz bo'ladi)</option>
                    <option value={UserRole.ADMIN}>Admin</option>
                    <option value={UserRole.DRIVER}>Haydovchi</option>
                    <option value={UserRole.CLIENT}>Mijoz</option>
                    <option value={UserRole.DISPATCHER}>Dispetcher</option>
                  </select>
                </div>
              </div>

              <div className="toggles-row">
                <div className="toggle-control">
                  <label>Tizimda faol (is_active)</label>
                  <button
                    className={`toggle-btn ${editActive ? "active" : ""}`}
                    onClick={() => setEditActive(!editActive)}
                  >
                    {editActive ? "Faol" : "Faol emas"}
                  </button>
                </div>

                <div className="toggle-control">
                  <label>Bloklash (is_banned)</label>
                  <button
                    className={`toggle-btn danger-toggle ${editBanned ? "active" : ""}`}
                    onClick={() => setEditBanned(!editBanned)}
                  >
                    {editBanned ? <UserX size={14} /> : <UserCheck size={14} />}
                    {editBanned ? "Bloklangan" : "Ruxsat etilgan"}
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setSelectedUser(null)} disabled={isSaving}>
                Bekor qilish
              </button>
              <button className="btn btn-primary" onClick={handleSaveUser} disabled={isSaving}>
                {isSaving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .users-page {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .filter-header {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .search-form {
          display: flex;
          position: relative;
          align-items: center;
          gap: 12px;
        }

        .search-icon {
          position: absolute;
          left: 16px;
          color: var(--text-muted);
        }

        .search-input {
          padding-left: 48px;
          flex: 1;
        }

        .filters-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
        }

        .filter-item {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--text-muted);
          min-width: 180px;
        }

        .filter-item select {
          padding: 8px 12px;
        }

        /* Table Card */
        .users-table-card {
          padding: 24px;
          min-height: 400px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .tg-id-badge {
          background: rgba(255, 255, 255, 0.04);
          border: var(--glass-border);
          padding: 4px 8px;
          border-radius: var(--border-radius-sm);
          font-size: 12px;
          font-family: monospace;
          color: var(--accent-secondary);
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }

        .user-name-cell {
          display: flex;
          flex-direction: column;
        }

        .user-fullname {
          font-weight: 600;
        }

        .user-username {
          font-size: 12px;
          color: var(--accent-secondary);
        }

        .row-banned td {
          opacity: 0.65;
          text-decoration: line-through rgba(255, 23, 68, 0.4);
        }

        .table-actions {
          display: flex;
          gap: 8px;
        }

        .table-loader {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          color: var(--text-secondary);
        }

        .empty-table {
          height: 300px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
        }

        .table-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 20px;
          border-top: 1px solid var(--border-color);
          padding-top: 20px;
        }

        .showing-text {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .pagination {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .page-indicator {
          font-size: 13px;
          font-weight: 500;
        }

        /* Modal specific overrides */
        .user-modal {
          max-width: 600px;
        }

        .user-modal-body {
          max-height: 70vh;
          overflow-y: auto;
        }

        .user-detail-header {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 20px;
        }

        .tg-username-line {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .user-meta-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 20px;
        }

        @media (max-width: 480px) {
          .user-meta-grid {
            grid-template-columns: 1fr;
          }
        }

        .meta-card {
          display: flex;
          align-items: center;
          gap: 12px;
          background: rgba(255, 255, 255, 0.02);
          border: var(--glass-border);
          padding: 12px;
          border-radius: var(--border-radius);
        }

        .meta-card svg {
          color: var(--accent-secondary);
        }

        .meta-card span {
          display: block;
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        .meta-card p {
          font-size: 13px;
          font-weight: 600;
        }

        .divider {
          height: 1px;
          background: var(--border-color);
          margin: 20px 0;
        }

        .edit-form-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 20px;
        }

        @media (max-width: 480px) {
          .edit-form-grid {
            grid-template-columns: 1fr;
          }
        }

        .toggles-row {
          display: flex;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 12px;
        }

        .toggle-control {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .toggle-control label {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-secondary);
        }

        .toggle-btn {
          padding: 12px;
          border: var(--glass-border);
          background: rgba(255, 255, 255, 0.02);
          border-radius: var(--border-radius);
          color: var(--text-secondary);
          font-family: var(--font-family);
          font-weight: 600;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .toggle-btn.active {
          background: var(--accent-primary);
          color: white;
          border-color: var(--accent-primary);
          box-shadow: 0 0 10px rgba(88, 101, 242, 0.3);
        }

        .danger-toggle.active {
          background: var(--danger);
          border-color: var(--danger);
          box-shadow: 0 0 10px rgba(255, 23, 68, 0.3);
        }
      `}</style>
    </div>
  );
};
