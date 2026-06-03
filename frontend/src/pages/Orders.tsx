import React, { useEffect, useState } from "react";
import { apiRequest } from "../api";
import type { Order, OrderUpdateData } from "../types";
import { OrderStatus } from "../types";
import {
  Filter,
  Eye,
  Trash2,
  X,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Calendar,
  Truck,
} from "lucide-react";

export const Orders: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filtering states
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const limit = 10;

  // Selected Order for Modal
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  
  // Edit form states
  const [editCargoName, setEditCargoName] = useState("");
  const [editWeight, setEditWeight] = useState(0);
  const [editPrice, setEditPrice] = useState(0);
  const [editStatus, setEditStatus] = useState<OrderStatus>(OrderStatus.PENDING);
  const [editCurrency, setEditCurrency] = useState("UZS");
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      let queryParams = `?skip=${skip}&limit=${limit}`;
      if (statusFilter) queryParams += `&status=${statusFilter}`;
      if (dateFrom) queryParams += `&date_from=${dateFrom}`;
      if (dateTo) queryParams += `&date_to=${dateTo}`;

      const data = await apiRequest<Order[]>(`/system/orders${queryParams}`);
      setOrders(data);
    } catch (err: any) {
      console.error("Failed to fetch orders:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [page, statusFilter, dateFrom, dateTo]);

  const handleOpenEdit = (order: Order) => {
    setSelectedOrder(order);
    setEditCargoName(order.cargo_name);
    setEditWeight(order.weight);
    setEditPrice(order.price);
    setEditStatus(order.status);
    setEditCurrency(order.currency);
    setErrorMsg("");
  };

  const handleSaveOrder = async () => {
    if (!selectedOrder) return;
    setIsSaving(true);
    setErrorMsg("");

    try {
      const payload: OrderUpdateData = {
        cargo_name: editCargoName,
        weight: Number(editWeight),
        price: Number(editPrice),
        currency: editCurrency,
        status: editStatus,
      };

      const updated = await apiRequest<Order>(`/system/orders/${selectedOrder.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      setOrders(orders.map(o => o.id === selectedOrder.id ? updated : o));
      setSelectedOrder(null);
    } catch (err: any) {
      setErrorMsg(err.message || "Buyurtmani yangilashda xatolik.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteOrder = async (orderId: number) => {
    if (!window.confirm("Haqiqatan ham bu buyurtmani butunlay o'chirib tashlamoqchimisiz?")) return;
    try {
      await apiRequest(`/system/orders/${orderId}`, {
        method: "DELETE",
      });
      setOrders(orders.filter(o => o.id !== orderId));
      setSelectedOrder(null);
    } catch (err: any) {
      alert(err.message || "O'chirishda xatolik.");
    }
  };

  const getStatusBadgeClass = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return "badge-warning";
      case OrderStatus.ACCEPTED:
        return "badge-primary";
      case OrderStatus.IN_PROGRESS:
        return "badge-info";
      case OrderStatus.COMPLETED:
        return "badge-success";
      case OrderStatus.CANCELLED:
        return "badge-danger";
      default:
        return "badge-neutral";
    }
  };

  // Get pickup and delivery addresses
  const getRouteAddresses = (order: Order) => {
    const sorted = [...order.waypoints].sort((a, b) => a.sequence - b.sequence);
    const pickup = sorted.find(w => w.waypoint_type === "pickup")?.address || "Kiritilmagan";
    const delivery = sorted.find(w => w.waypoint_type === "delivery")?.address || "Kiritilmagan";
    return { pickup, delivery };
  };

  return (
    <div className="orders-page">
      {/* FILTER BAR */}
      <div className="filter-header glass-card">
        <div className="filters-row flex-between">
          <div className="filter-item select-filter">
            <Filter size={14} />
            <select className="glass-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="">Barcha Statuslar</option>
              <option value={OrderStatus.PENDING}>Pending (Kutilmoqda)</option>
              <option value={OrderStatus.ACCEPTED}>Accepted (Qabul qilindi)</option>
              <option value={OrderStatus.IN_PROGRESS}>In Progress (Yo'lda)</option>
              <option value={OrderStatus.COMPLETED}>Completed (Tugatilgan)</option>
              <option value={OrderStatus.CANCELLED}>Cancelled (Bekor qilingan)</option>
            </select>
          </div>

          <div className="date-filters">
            <div className="filter-item date-input-wrap">
              <Calendar size={14} />
              <input type="date" className="glass-input date-input" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />
            </div>
            <span className="date-separator">dan</span>
            <div className="filter-item date-input-wrap">
              <Calendar size={14} />
              <input type="date" className="glass-input date-input" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />
            </div>
          </div>
        </div>
      </div>

      {/* ORDERS LIST */}
      <div className="orders-table-card glass-card">
        {loading ? (
          <div className="table-loader">
            <div className="spinner"></div>
            <p>Buyurtmalar yuklanmoqda...</p>
          </div>
        ) : orders.length > 0 ? (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Yuk Nomi</th>
                  <th>Og'irligi (Tonna)</th>
                  <th>Yo'nalish (Kuzatuv)</th>
                  <th>Narxi</th>
                  <th>Status</th>
                  <th>Haydovchi</th>
                  <th>Sana</th>
                  <th>Amallar</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => {
                  const { pickup, delivery } = getRouteAddresses(o);
                  return (
                    <tr key={o.id}>
                      <td>
                        <span className="order-id-badge">#{o.id}</span>
                      </td>
                      <td>
                        <span className="cargo-name-bold">{o.cargo_name}</span>
                      </td>
                      <td>{o.weight} t</td>
                      <td>
                        <div className="route-cell">
                          <span className="addr" title={pickup}><MapPin size={10} color="var(--success)" /> {pickup.split(",")[0]}</span>
                          <span className="arrow-down">↓</span>
                          <span className="addr" title={delivery}><MapPin size={10} color="var(--danger)" /> {delivery.split(",")[0]}</span>
                        </div>
                      </td>
                      <td>
                        <span className="price-tag">{Number(o.price).toLocaleString()} {o.currency}</span>
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadgeClass(o.status)}`}>
                          {o.status}
                        </span>
                      </td>
                      <td>
                        {o.driver_id ? (
                          <span className="driver-assigned"><Truck size={12} /> ID: {o.driver_id}</span>
                        ) : (
                          <span className="text-muted">Tayinlanmagan</span>
                        )}
                      </td>
                      <td>{new Date(o.created_at).toLocaleDateString()}</td>
                      <td>
                        <div className="table-actions">
                          <button className="btn btn-secondary btn-icon" title="Ko'rish / Tahrirlash" onClick={() => handleOpenEdit(o)}>
                            <Eye size={14} />
                          </button>
                          <button className="btn btn-secondary btn-icon text-danger" title="O'chirish" onClick={() => handleDeleteOrder(o.id)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-table">Hech qanday buyurtma topilmadi.</div>
        )}

        {/* PAGINATION */}
        <div className="table-footer">
          <span className="showing-text">
            Buyurtmalar ro'yxati (Sahifada: {orders.length} ta)
          </span>
          <div className="pagination">
            <button className="btn btn-secondary btn-icon" onClick={() => setPage(p => Math.max(p - 1, 1))} disabled={page === 1}>
              <ChevronLeft size={16} />
            </button>
            <span className="page-indicator">Sahifa {page}</span>
            <button className="btn btn-secondary btn-icon" onClick={() => setPage(p => p + 1)} disabled={orders.length < limit}>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* DETAIL & EDIT MODAL */}
      {selectedOrder && (
        <div className="modal-backdrop">
          <div className="glass-card modal-content animate-slide-in order-modal">
            <div className="modal-header">
              <h3>Buyurtma Moderatsiyasi #{selectedOrder.id}</h3>
              <button className="close-btn" onClick={() => setSelectedOrder(null)}>
                <X size={18} />
              </button>
            </div>

            {errorMsg && <div className="alert-message danger-alert">{errorMsg}</div>}

            <div className="modal-body order-modal-body">
              {/* Order stats review */}
              <div className="order-stats-bar">
                <div className="stat-pill">
                  <span>Mijoz ID</span>
                  <p>{selectedOrder.customer_id}</p>
                </div>
                <div className="stat-pill">
                  <span>Masofa</span>
                  <p>{selectedOrder.total_distance_km ? `${selectedOrder.total_distance_km} km` : "Hisoblanmagan"}</p>
                </div>
                <div className="stat-pill">
                  <span>Hajmi</span>
                  <p>{selectedOrder.volume ? `${selectedOrder.volume} m³` : "Kiritilmagan"}</p>
                </div>
                <div className="stat-pill">
                  <span>Sana</span>
                  <p>{new Date(selectedOrder.created_at).toLocaleDateString()}</p>
                </div>
              </div>

              {/* Waypoints timeline */}
              <div className="timeline-container">
                <h5><MapPin size={14} /> Marshrut nuqtalari</h5>
                <div className="timeline">
                  {selectedOrder.waypoints.map((w, index) => (
                    <div className="timeline-item" key={w.id}>
                      <div className="timeline-dot-wrapper">
                        <div className={`timeline-dot ${w.waypoint_type === "pickup" ? "dot-pickup" : w.waypoint_type === "delivery" ? "dot-delivery" : "dot-transit"}`}></div>
                        {index < selectedOrder.waypoints.length - 1 && <div className="timeline-line"></div>}
                      </div>
                      <div className="timeline-content">
                        <div className="timeline-header-row">
                          <span className="point-type-badge">{w.waypoint_type.toUpperCase()} ({w.sequence})</span>
                          {w.contact_name && <span className="contact-name">{w.contact_name}: {w.contact_phone}</span>}
                        </div>
                        <p className="point-addr">{w.address}</p>
                        {w.note && <p className="point-note"><b>Eslatma:</b> {w.note}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="divider"></div>

              {/* Editable form fields */}
              <div className="edit-form-grid">
                <div className="form-group">
                  <label>Yuk Nomi:</label>
                  <input
                    type="text"
                    className="glass-input"
                    value={editCargoName}
                    onChange={(e) => setEditCargoName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Yuk Og'irligi (tonna):</label>
                  <input
                    type="number"
                    step="0.1"
                    className="glass-input"
                    value={editWeight}
                    onChange={(e) => setEditWeight(Number(e.target.value))}
                  />
                </div>

                <div className="form-group">
                  <label>Taklif etilgan Narx:</label>
                  <input
                    type="number"
                    className="glass-input"
                    value={editPrice}
                    onChange={(e) => setEditPrice(Number(e.target.value))}
                  />
                </div>

                <div className="form-group">
                  <label>Status:</label>
                  <select
                    className="glass-select"
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as OrderStatus)}
                  >
                    <option value={OrderStatus.PENDING}>Pending</option>
                    <option value={OrderStatus.ACCEPTED}>Accepted</option>
                    <option value={OrderStatus.IN_PROGRESS}>In Progress</option>
                    <option value={OrderStatus.COMPLETED}>Completed</option>
                    <option value={OrderStatus.CANCELLED}>Cancelled</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary btn-icon text-danger" title="Butunlay o'chirish" onClick={() => handleDeleteOrder(selectedOrder.id)}>
                <Trash2 size={16} /> O'chirish
              </button>
              <div className="right-footer-btns">
                <button className="btn btn-secondary" onClick={() => setSelectedOrder(null)} disabled={isSaving}>
                  Bekor qilish
                </button>
                <button className="btn btn-primary" onClick={handleSaveOrder} disabled={isSaving}>
                  {isSaving ? "Saqlanmoqda..." : "Saqlash"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .orders-page {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .flex-between {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
          flex-wrap: wrap;
          gap: 16px;
        }

        .select-filter {
          min-width: 220px;
        }

        .date-filters {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .date-input-wrap {
          position: relative;
        }

        .date-input {
          padding: 8px 12px;
          font-size: 13px;
        }

        .date-separator {
          font-size: 13px;
          color: var(--text-muted);
        }

        .order-id-badge {
          background: rgba(88, 101, 242, 0.08);
          border: 1px solid rgba(88, 101, 242, 0.2);
          color: #8c9eff;
          padding: 4px 8px;
          border-radius: var(--border-radius-sm);
          font-weight: 700;
          font-size: 12px;
        }

        .cargo-name-bold {
          font-weight: 600;
        }

        .route-cell {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .route-cell .addr {
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 180px;
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .arrow-down {
          font-size: 11px;
          color: var(--text-muted);
          padding-left: 4px;
        }

        .price-tag {
          font-weight: 700;
          color: var(--accent-secondary);
        }

        .driver-assigned {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          font-weight: 600;
          color: var(--success);
        }

        /* Order Modal */
        .order-modal {
          max-width: 680px;
        }

        .order-modal-body {
          max-height: 70vh;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .order-stats-bar {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          background: rgba(0, 0, 0, 0.15);
          padding: 16px;
          border-radius: var(--border-radius);
          border: var(--glass-border);
        }

        @media (max-width: 480px) {
          .order-stats-bar {
            grid-template-columns: 1fr 1fr;
          }
        }

        .stat-pill span {
          display: block;
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        .stat-pill p {
          font-size: 14px;
          font-weight: 700;
        }

        /* Timeline */
        .timeline-container h5 {
          font-size: 13px;
          font-weight: 700;
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 12px;
        }

        .timeline {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .timeline-item {
          display: flex;
          gap: 16px;
        }

        .timeline-dot-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .timeline-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }

        .dot-pickup { background: var(--success); box-shadow: 0 0 8px var(--success-glow); }
        .dot-delivery { background: var(--danger); box-shadow: 0 0 8px var(--danger-glow); }
        .dot-transit { background: var(--warning); }

        .timeline-line {
          width: 2px;
          flex: 1;
          background: var(--border-color);
          margin-top: 4px;
        }

        .timeline-content {
          flex: 1;
          background: rgba(255, 255, 255, 0.01);
          border: var(--glass-border);
          border-radius: var(--border-radius);
          padding: 12px 16px;
        }

        .timeline-header-row {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
          margin-bottom: 4px;
        }

        .point-type-badge {
          font-weight: 700;
          color: var(--accent-secondary);
        }

        .contact-name {
          color: var(--text-muted);
        }

        .point-addr {
          font-size: 13px;
          font-weight: 600;
        }

        .point-note {
          font-size: 12px;
          color: var(--text-secondary);
          margin-top: 4px;
        }

        .right-footer-btns {
          display: flex;
          gap: 12px;
        }
      `}</style>
    </div>
  );
};
