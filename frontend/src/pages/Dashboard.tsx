import React, { useEffect, useState } from "react";
import { apiRequest } from "../api";
import type { AdminDashboardStats } from "../types";
import {
  Users,
  Truck,
  TrendingUp,
  Brain,
  Layers,
  ArrowUpRight,
  RefreshCw,
  Cpu,
  Clock,
} from "lucide-react";

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchStats = async () => {
    setIsRefreshing(true);
    try {
      const data = await apiRequest<AdminDashboardStats>("/system/dashboard/stats");
      setStats(data);
      setError("");
    } catch (err: any) {
      setError(err.message || "Statistikalarni yuklashda xatolik.");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 60s
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="center-loader">
        <div className="spinner"></div>
        <p>Dashboard ma'lumotlari yuklanmoqda...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-state glass-card">
        <p>{error}</p>
        <button className="btn btn-primary" onClick={fetchStats}>
          Qayta urinish
        </button>
      </div>
    );
  }

  // Calculate some helpers
  const totalTokens = (stats?.ai_input_tokens_today || 0) + (stats?.ai_output_tokens_today || 0);

  // SVG Chart settings
  const chartHeight = 120;
  const chartWidth = 500;
  const padding = 20;

  const getChartPoints = () => {
    if (!stats || !stats.orders_last_7_days.length) return "";
    const data = stats.orders_last_7_days;
    const maxVal = Math.max(...data.map(d => d.count), 5); // default min height

    return data
      .map((d, index) => {
        const x = padding + (index * (chartWidth - padding * 2)) / (data.length - 1);
        const y = chartHeight - padding - (d.count * (chartHeight - padding * 2)) / maxVal;
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="dashboard-page">
      <div className="actions-bar">
        <span className="last-update">
          <Clock size={14} /> Oxirgi yangilanish: {new Date().toLocaleTimeString()}
        </span>
        <button className={`btn btn-secondary ${isRefreshing ? "spin-icon" : ""}`} onClick={fetchStats} disabled={isRefreshing}>
          <RefreshCw size={16} /> Yangilash
        </button>
      </div>

      {/* STATS CARDS GRID */}
      <div className="stats-grid">
        <div className="stats-card glass-card">
          <div className="card-header">
            <div className="icon-wrapper blue-glow">
              <Users size={22} />
            </div>
            <span className="card-label">Foydalanuvchilar</span>
          </div>
          <div className="card-body">
            <h3>{stats?.users_total || 0}</h3>
            <span className="trend positive">
              <ArrowUpRight size={14} /> +{stats?.users_today || 0} bugun
            </span>
          </div>
        </div>

        <div className="stats-card glass-card">
          <div className="card-header">
            <div className="icon-wrapper green-glow">
              <Truck size={22} />
            </div>
            <span className="card-label">Haydovchilar (Online)</span>
          </div>
          <div className="card-body">
            <h3>{stats?.drivers_online || 0} <span className="slash">/</span> {stats?.drivers_total || 0}</h3>
            <span className="trend neutral">
              GPS faol: {stats?.drivers_live_gps || 0}
            </span>
          </div>
        </div>

        <div className="stats-card glass-card">
          <div className="card-header">
            <div className="icon-wrapper orange-glow">
              <TrendingUp size={22} />
            </div>
            <span className="card-label">Bugungi Buyurtmalar</span>
          </div>
          <div className="card-body">
            <h3>{stats?.orders_today || 0}</h3>
            <span className="trend positive">
              Jami: {stats?.orders_total || 0} ta
            </span>
          </div>
        </div>

        <div className="stats-card glass-card">
          <div className="card-header">
            <div className="icon-wrapper purple-glow">
              <Brain size={22} />
            </div>
            <span className="card-label">AI Agent So'rovlari</span>
          </div>
          <div className="card-body">
            <h3>{stats?.ai_requests_today || 0}</h3>
            <span className="trend positive">
              Takliflar: {stats?.offers_today || 0} ta
            </span>
          </div>
        </div>
      </div>

      <div className="dashboard-content-layout">
        {/* LEFT COLUMN: CHART & STATUSES */}
        <div className="content-col col-left">
          {/* ORDERS CHART CARD */}
          <div className="chart-card glass-card">
            <div className="section-title">
              <h4>Oxirgi 7 kundagi buyurtmalar</h4>
            </div>
            <div className="svg-container">
              {stats && stats.orders_last_7_days.length > 0 ? (
                <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="trend-svg">
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent-secondary)" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="var(--accent-secondary)" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Fill Area */}
                  <polygon
                    points={`${padding},${chartHeight - padding} ${getChartPoints()} ${chartWidth - padding},${chartHeight - padding}`}
                    fill="url(#chartGradient)"
                  />
                  {/* Trend Line */}
                  <polyline
                    fill="none"
                    stroke="var(--accent-secondary)"
                    strokeWidth="3"
                    points={getChartPoints()}
                  />
                  {/* Data Points */}
                  {stats.orders_last_7_days.map((d, index) => {
                    const maxVal = Math.max(...stats.orders_last_7_days.map(x => x.count), 5);
                    const x = padding + (index * (chartWidth - padding * 2)) / (stats.orders_last_7_days.length - 1);
                    const y = chartHeight - padding - (d.count * (chartHeight - padding * 2)) / maxVal;
                    return (
                      <g key={index} className="point-group">
                        <circle cx={x} cy={y} r="5" fill="var(--bg-primary)" stroke="var(--accent-secondary)" strokeWidth="2" />
                        <text x={x} y={y - 8} textAnchor="middle" className="chart-text" fontSize="9" fill="var(--text-primary)">
                          {d.count}
                        </text>
                      </g>
                    );
                  })}
                  {/* X Axis Labels */}
                  {stats.orders_last_7_days.map((d, index) => {
                    const x = padding + (index * (chartWidth - padding * 2)) / (stats.orders_last_7_days.length - 1);
                    // Format date to DD/MM
                    const dateObj = new Date(d.date);
                    const label = `${dateObj.getDate()}.${dateObj.getMonth() + 1}`;
                    return (
                      <text key={index} x={x} y={chartHeight - 4} textAnchor="middle" className="axis-text" fontSize="9" fill="var(--text-muted)">
                        {label}
                      </text>
                    );
                  })}
                </svg>
              ) : (
                <div className="no-data">Ma'lumotlar mavjud emas</div>
              )}
            </div>
          </div>

          {/* AI TOKENS USAGE CARD */}
          <div className="tokens-card glass-card">
            <div className="section-title">
              <Cpu size={16} />
              <h4>Bugungi AI Tokenlar Sarfi</h4>
            </div>
            <div className="tokens-usage-content">
              <div className="token-radial-row">
                <div className="token-progress-bar">
                  <div className="bar-track"></div>
                  <div className="bar-fill" style={{ width: `${Math.min((totalTokens / 500000) * 100, 100)}%` }}></div>
                </div>
                <div className="token-nums">
                  <span className="total-tokens">{totalTokens.toLocaleString()} / 500k tokens</span>
                  <span className="limit-lbl">Maksimal limit</span>
                </div>
              </div>
              <div className="tokens-grid">
                <div className="token-subcard">
                  <h5>Input Tokens</h5>
                  <p>{stats?.ai_input_tokens_today.toLocaleString() || 0}</p>
                </div>
                <div className="token-subcard">
                  <h5>Output Tokens</h5>
                  <p>{stats?.ai_output_tokens_today.toLocaleString() || 0}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: ORDERS BREAKDOWN */}
        <div className="content-col col-right">
          <div className="breakdown-card glass-card">
            <div className="section-title">
              <Layers size={16} />
              <h4>Buyurtmalar Statusi Bo'yicha</h4>
            </div>
            <div className="breakdown-list">
              {stats && Object.entries(stats.orders_by_status).length > 0 ? (
                Object.entries(stats.orders_by_status).map(([status, count]) => {
                  const maxCount = Math.max(...Object.values(stats.orders_by_status), 1);
                  const percentage = (count / maxCount) * 100;
                  
                  // Style colors per status
                  let colorClass = "bar-blue";
                  if (status === "completed") colorClass = "bar-green";
                  if (status === "cancelled") colorClass = "bar-red";
                  if (status === "in_progress") colorClass = "bar-orange";

                  return (
                    <div className="breakdown-item" key={status}>
                      <div className="item-label-row">
                        <span className="status-name">{status.toUpperCase()}</span>
                        <span className="status-count">{count} ta</span>
                      </div>
                      <div className="status-progress">
                        <div className={`status-fill ${colorClass}`} style={{ width: `${percentage}%` }}></div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="no-data">Hech qanday buyurtma mavjud emas</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .dashboard-page {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .actions-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .last-update {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: var(--text-secondary);
        }

        .spin-icon svg {
          animation: spin 1s linear infinite;
        }

        /* Stats Grid */
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 20px;
        }

        .stats-card {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .card-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .icon-wrapper {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .blue-glow { background: var(--accent-primary); box-shadow: 0 0 15px rgba(88, 101, 242, 0.4); }
        .green-glow { background: var(--success); box-shadow: 0 0 15px rgba(0, 230, 118, 0.4); }
        .orange-glow { background: var(--warning); box-shadow: 0 0 15px rgba(255, 179, 0, 0.4); }
        .purple-glow { background: #9c27b0; box-shadow: 0 0 15px rgba(156, 39, 176, 0.4); }

        .card-label {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
        }

        .card-body h3 {
          font-size: 28px;
          font-weight: 800;
          letter-spacing: -0.02em;
        }

        .slash {
          color: var(--text-muted);
          font-size: 20px;
        }

        .trend {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          font-weight: 600;
          margin-top: 4px;
        }

        .trend.positive { color: var(--success); }
        .trend.neutral { color: var(--accent-secondary); }

        /* Dashboard Content Layout */
        .dashboard-content-layout {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 20px;
        }

        @media (max-width: 992px) {
          .dashboard-content-layout {
            grid-template-columns: 1fr;
          }
        }

        .content-col {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 20px;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 12px;
        }

        .section-title h4 {
          font-size: 15px;
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        /* Chart Card */
        .chart-card {
          padding: 24px;
        }

        .svg-container {
          width: 100%;
          padding-top: 10px;
        }

        .trend-svg {
          width: 100%;
          overflow: visible;
        }

        .chart-text {
          font-weight: 700;
        }

        .axis-text {
          font-weight: 500;
        }

        .no-data {
          height: 120px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
          font-size: 13px;
        }

        /* Tokens Card */
        .tokens-card {
          padding: 24px;
        }

        .tokens-usage-content {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .token-radial-row {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .token-progress-bar {
          position: relative;
          height: 8px;
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
          overflow: hidden;
        }

        .bar-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
          border-radius: 4px;
        }

        .token-nums {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
        }

        .total-tokens {
          font-weight: 700;
          color: var(--text-primary);
        }

        .limit-lbl {
          color: var(--text-muted);
        }

        .tokens-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .token-subcard {
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid var(--border-color);
          padding: 16px;
          border-radius: var(--border-radius);
        }

        .token-subcard h5 {
          font-size: 11px;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 4px;
        }

        .token-subcard p {
          font-size: 18px;
          font-weight: 700;
        }

        /* Breakdown Card */
        .breakdown-card {
          padding: 24px;
          height: 100%;
        }

        .breakdown-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .breakdown-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .item-label-row {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 600;
        }

        .status-name {
          color: var(--text-secondary);
        }

        .status-count {
          color: var(--text-primary);
        }

        .status-progress {
          height: 6px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 3px;
          overflow: hidden;
        }

        .status-fill {
          height: 100%;
          border-radius: 3px;
        }

        .bar-blue { background: var(--accent-primary); }
        .bar-green { background: var(--success); }
        .bar-red { background: var(--danger); }
        .bar-orange { background: var(--warning); }

        .center-loader {
          height: calc(100vh - 200px);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 16px;
          color: var(--text-secondary);
        }

        .error-state {
          padding: 40px;
          text-align: center;
          margin-top: 40px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
        }
      `}</style>
    </div>
  );
};
