import { useEffect, useMemo, useState } from "react";
import {
  acceptOffer,
  assignDriver,
  changeMyPassword,
  createOffer,
  createOrder,
  createTruckType,
  deleteMyAccount,
  deleteOffer,
  deleteOrder,
  deleteTruckType,
  ensureSession,
  getAllTruckTypes,
  getMyProfile,
  getOffer,
  getOrder,
  getTruckTypeById,
  listOffersByDriver,
  listOffersForOrder,
  listOrders,
  updateMyProfile,
  updateOffer,
  updateOfferStatus,
  updateOrder,
  updateOrderStatus,
  updateTruckType,
} from "./api/client";
import { hydrateAccessToken } from "./auth/session";

function getTelegramInitData() {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    throw new Error("Telegram WebApp SDK topilmadi");
  }
  tg.ready();
  tg.expand();
  return tg.initData;
}

const PAYLOAD_TEMPLATES = {
  orderCreate: {
    cargo_name: "Olma",
    weight: 10,
    volume: 2,
    from_city: "Toshkent",
    to_city: "Samarqand",
    distance_km: 300,
    required_truck_type_id: 1,
    price: 1500000,
    currency: "UZS",
    pickup_date: "2026-04-30T09:00:00",
    delivery_date: "2026-04-30T20:00:00",
  },
  orderUpdate: {
    from_city: "Andijon",
    to_city: "Buxoro",
    price: 1800000,
  },
  offerCreate: {
    offered_price: 1450000,
    estimated_arrival_time: "2026-05-01T08:30:00",
    comment: "Tez yetkazib beraman",
  },
  offerUpdate: {
    offered_price: 1400000,
    comment: "Narxni yangiladim",
  },
  truckTypeCreate: {
    name: "Isuzu 5T",
    max_weight: 5,
    max_volume: 25,
    length: 6.2,
    width: 2.3,
    height: 2.2,
    pallet_capacity: 12,
    description: "Shaharlararo tashuv",
  },
  truckTypeUpdate: {
    max_weight: 6,
    max_volume: 28,
    description: "Yangilangan konfiguratsiya",
  },
  profileUpdate: {
    full_name: "Test User",
    phone_number: "+998901112233",
    language: "uz",
  },
  passwordUpdate: {
    old_password: "OldPassword123",
    new_password: "NewPassword123",
  },
};

const TEMPLATE_OPTIONS = [
  { id: "orderCreate", label: "Order create" },
  { id: "orderUpdate", label: "Order update" },
  { id: "offerCreate", label: "Offer create" },
  { id: "offerUpdate", label: "Offer update" },
  { id: "truckTypeCreate", label: "Truck type create" },
  { id: "truckTypeUpdate", label: "Truck type update" },
  { id: "profileUpdate", label: "Profile update" },
  { id: "passwordUpdate", label: "Password update" },
];

function templateToText(templateId) {
  return JSON.stringify(PAYLOAD_TEMPLATES[templateId], null, 2);
}

function toInt(value, fieldLabel) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${fieldLabel} musbat son bo'lishi kerak.`);
  }
  return parsed;
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState(null);
  const [activeTab, setActiveTab] = useState("profile");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [actionError, setActionError] = useState("");
  const [requestHistory, setRequestHistory] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState("orderCreate");
  const [input, setInput] = useState({
    customerId: "",
    driverId: "",
    orderId: "",
    offerId: "",
    truckTypeId: "",
    fromCity: "",
    toCity: "",
    skip: "0",
    limit: "20",
    orderStatus: "pending",
    offerStatus: "pending",
    payload: templateToText("orderCreate"),
  });

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        hydrateAccessToken();
        const initData = getTelegramInitData();
        if (!initData) {
          throw new Error("initData bo'sh");
        }
        await ensureSession(initData);
        const me = await getMyProfile();
        if (mounted) {
          setProfile(me);
        }
      } catch (err) {
        if (mounted) {
          setError(err?.response?.data?.detail || err.message || "Xatolik yuz berdi");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  const tabs = useMemo(
    () => [
      { id: "profile", label: "Profile/Auth" },
      { id: "orders", label: "Orders" },
      { id: "offers", label: "Offers" },
      { id: "drivers", label: "Driver/Truck" },
    ],
    []
  );

  function parsePayload() {
    if (!input.payload.trim()) {
      return {};
    }
    return JSON.parse(input.payload);
  }

  function hydrateTemplate(templateId) {
    setSelectedTemplate(templateId);
    setInput((prev) => ({
      ...prev,
      payload: templateToText(templateId),
    }));
  }

  async function run(action, meta) {
    setBusy(true);
    setActionError("");
    const startAt = Date.now();
    try {
      const data = await action();
      setResult(data);
      setRequestHistory((prev) => [
        {
          id: Date.now(),
          endpoint: meta,
          ok: true,
          ms: Date.now() - startAt,
        },
        ...prev.slice(0, 11),
      ]);
    } catch (err) {
      const message = err?.response?.data?.detail || err.message || "Xatolik";
      setActionError(message);
      setRequestHistory((prev) => [
        {
          id: Date.now(),
          endpoint: meta,
          ok: false,
          ms: Date.now() - startAt,
          message,
        },
        ...prev.slice(0, 11),
      ]);
    } finally {
      setBusy(false);
    }
  }

  const resultStats = useMemo(() => {
    if (Array.isArray(result)) {
      return `Array: ${result.length} ta element`;
    }
    if (result && typeof result === "object") {
      return `Object: ${Object.keys(result).length} ta maydon`;
    }
    return "Natija mavjud emas";
  }, [result]);

  if (loading) {
    return <main className="card">Yuklanmoqda...</main>;
  }
  if (error) {
    return <main className="card error">Xatolik: {error}</main>;
  }

  return (
    <main className="layout">
      <section className="card">
        <h1>Logistika API Panel</h1>
        <p>
          Salom, <strong>{profile?.full_name}</strong> (ID: {profile?.id})
        </p>
        <p className="muted">
          Ushbu panel orqali barcha API router endpointlarini test qilishingiz mumkin.
        </p>

        <div className="tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="inputs-grid">
          <input
            placeholder="customer_id"
            value={input.customerId}
            onChange={(e) => setInput((p) => ({ ...p, customerId: e.target.value }))}
          />
          <input
            placeholder="driver_id"
            value={input.driverId}
            onChange={(e) => setInput((p) => ({ ...p, driverId: e.target.value }))}
          />
          <input
            placeholder="order_id"
            value={input.orderId}
            onChange={(e) => setInput((p) => ({ ...p, orderId: e.target.value }))}
          />
          <input
            placeholder="offer_id"
            value={input.offerId}
            onChange={(e) => setInput((p) => ({ ...p, offerId: e.target.value }))}
          />
          <input
            placeholder="truck_type_id"
            value={input.truckTypeId}
            onChange={(e) => setInput((p) => ({ ...p, truckTypeId: e.target.value }))}
          />
          <input
            placeholder="from_city filter"
            value={input.fromCity}
            onChange={(e) => setInput((p) => ({ ...p, fromCity: e.target.value }))}
          />
          <input
            placeholder="to_city filter"
            value={input.toCity}
            onChange={(e) => setInput((p) => ({ ...p, toCity: e.target.value }))}
          />
          <input
            placeholder="skip"
            value={input.skip}
            onChange={(e) => setInput((p) => ({ ...p, skip: e.target.value }))}
          />
          <input
            placeholder="limit"
            value={input.limit}
            onChange={(e) => setInput((p) => ({ ...p, limit: e.target.value }))}
          />
          <select
            value={input.orderStatus}
            onChange={(e) => setInput((p) => ({ ...p, orderStatus: e.target.value }))}
          >
            <option value="pending">pending</option>
            <option value="accepted">accepted</option>
            <option value="in_progress">in_progress</option>
            <option value="completed">completed</option>
            <option value="cancelled">cancelled</option>
          </select>
          <select
            value={input.offerStatus}
            onChange={(e) => setInput((p) => ({ ...p, offerStatus: e.target.value }))}
          >
            <option value="pending">pending</option>
            <option value="accepted">accepted</option>
            <option value="rejected">rejected</option>
            <option value="cancelled">cancelled</option>
          </select>
        </div>

        <div className="template-row">
          <select value={selectedTemplate} onChange={(e) => hydrateTemplate(e.target.value)}>
            {TEMPLATE_OPTIONS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => setInput((p) => ({ ...p, payload: "{}" }))}>
            Payloadni tozalash
          </button>
          <button
            type="button"
            onClick={() =>
              setInput((p) => ({
                ...p,
                customerId: String(profile?.id || ""),
              }))
            }
          >
            customer_id = my id
          </button>
        </div>

        <textarea
          className="payload"
          value={input.payload}
          onChange={(e) => setInput((p) => ({ ...p, payload: e.target.value }))}
        />

        {activeTab === "profile" && (
          <div className="actions">
            <button type="button" onClick={() => run(() => getMyProfile(), "GET /auth/me")}>
              GET /auth/me
            </button>
            <button
              type="button"
              onClick={() => run(() => updateMyProfile(parsePayload()), "PATCH /auth/me")}
            >
              PATCH /auth/me
            </button>
            <button
              type="button"
              onClick={() =>
                run(() => changeMyPassword(parsePayload()), "PATCH /auth/me/password")
              }
            >
              PATCH /auth/me/password
            </button>
            <button
              type="button"
              className="danger"
              onClick={() => run(() => deleteMyAccount(), "DELETE /auth/me")}
            >
              DELETE /auth/me
            </button>
          </div>
        )}

        {activeTab === "orders" && (
          <div className="actions">
            <button
              type="button"
              onClick={() =>
                run(
                  () =>
                    listOrders({
                      customer_id: input.customerId || undefined,
                      driver_id: input.driverId || undefined,
                      status: input.orderStatus || undefined,
                      from_city: input.fromCity || undefined,
                      to_city: input.toCity || undefined,
                      skip: Number(input.skip) || 0,
                      limit: Number(input.limit) || 20,
                    }),
                  "GET /orders"
                )
              }
            >
              GET /orders
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => createOrder(parsePayload(), toInt(input.customerId, "customer_id")),
                  "POST /orders"
                )
              }
            >
              POST /orders
            </button>
            <button
              type="button"
              onClick={() => run(() => getOrder(toInt(input.orderId, "order_id")), "GET /orders/{order_id}")}
            >
              GET /orders/{`{order_id}`}
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => updateOrder(toInt(input.orderId, "order_id"), parsePayload()),
                  "PATCH /orders/{order_id}"
                )
              }
            >
              PATCH /orders/{`{order_id}`}
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => updateOrderStatus(toInt(input.orderId, "order_id"), input.orderStatus),
                  "PATCH /orders/{order_id}/status"
                )
              }
            >
              PATCH /orders/{`{order_id}`}/status
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () =>
                    assignDriver(
                      toInt(input.orderId, "order_id"),
                      toInt(input.driverId, "driver_id")
                    ),
                  "PATCH /orders/{order_id}/assign-driver"
                )
              }
            >
              PATCH /orders/{`{order_id}`}/assign-driver
            </button>
            <button
              type="button"
              className="danger"
              onClick={() =>
                run(() => deleteOrder(toInt(input.orderId, "order_id")), "DELETE /orders/{order_id}")
              }
            >
              DELETE /orders/{`{order_id}`}
            </button>
          </div>
        )}

        {activeTab === "offers" && (
          <div className="actions">
            <button
              type="button"
              onClick={() =>
                run(
                  () =>
                    createOffer(
                      toInt(input.orderId, "order_id"),
                      parsePayload(),
                      toInt(input.driverId, "driver_id")
                    ),
                  "POST /orders/{order_id}/offers"
                )
              }
            >
              POST /orders/{`{order_id}`}/offers
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => listOffersForOrder(toInt(input.orderId, "order_id"), input.offerStatus),
                  "GET /orders/{order_id}/offers"
                )
              }
            >
              GET /orders/{`{order_id}`}/offers
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () =>
                    listOffersByDriver(toInt(input.driverId, "driver_id"), {
                      status: input.offerStatus,
                      skip: Number(input.skip) || 0,
                      limit: Number(input.limit) || 20,
                    }),
                  "GET /drivers/{driver_id}/offers"
                )
              }
            >
              GET /drivers/{`{driver_id}`}/offers
            </button>
            <button
              type="button"
              onClick={() => run(() => getOffer(toInt(input.offerId, "offer_id")), "GET /offers/{offer_id}")}
            >
              GET /offers/{`{offer_id}`}
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => updateOffer(toInt(input.offerId, "offer_id"), parsePayload()),
                  "PATCH /offers/{offer_id}"
                )
              }
            >
              PATCH /offers/{`{offer_id}`}
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => updateOfferStatus(toInt(input.offerId, "offer_id"), input.offerStatus),
                  "PATCH /offers/{offer_id}/status"
                )
              }
            >
              PATCH /offers/{`{offer_id}`}/status
            </button>
            <button
              type="button"
              onClick={() =>
                run(() => acceptOffer(toInt(input.offerId, "offer_id")), "POST /offers/{offer_id}/accept")
              }
            >
              POST /offers/{`{offer_id}`}/accept
            </button>
            <button
              type="button"
              className="danger"
              onClick={() =>
                run(() => deleteOffer(toInt(input.offerId, "offer_id")), "DELETE /offers/{offer_id}")
              }
            >
              DELETE /offers/{`{offer_id}`}
            </button>
          </div>
        )}

        {activeTab === "drivers" && (
          <div className="actions">
            <button type="button" onClick={() => run(() => getAllTruckTypes(), "GET /driver/truck-type-get_all")}>
              GET /driver/truck-type-get_all
            </button>
            <button
              type="button"
              onClick={() => run(() => createTruckType(parsePayload()), "POST /driver/truck-type-create")}
            >
              POST /driver/truck-type-create
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => getTruckTypeById(toInt(input.truckTypeId, "truck_type_id")),
                  "GET /driver/get_truck_type/{pk}"
                )
              }
            >
              GET /driver/get_truck_type/{`{pk}`}
            </button>
            <button
              type="button"
              onClick={() =>
                run(
                  () => updateTruckType(toInt(input.truckTypeId, "truck_type_id"), parsePayload()),
                  "PUT /driver/truck-type-update/{pk}"
                )
              }
            >
              PUT /driver/truck-type-update/{`{pk}`}
            </button>
            <button
              type="button"
              className="danger"
              onClick={() =>
                run(
                  () => deleteTruckType(toInt(input.truckTypeId, "truck_type_id")),
                  "DELETE /driver/delete_truck_type/{pk}"
                )
              }
            >
              DELETE /driver/delete_truck_type/{`{pk}`}
            </button>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Natija</h2>
        {busy && <p>So‘rov yuborilmoqda...</p>}
        {actionError && <p className="error-text">Xatolik: {actionError}</p>}
        <p className="muted">{resultStats}</p>
        <pre>{result ? JSON.stringify(result, null, 2) : "Hali so‘rov yuborilmadi"}</pre>

        <h3>So'rovlar tarixi</h3>
        <div className="history">
          {requestHistory.length === 0 && <p className="muted">Tarix bo'sh</p>}
          {requestHistory.map((item) => (
            <div key={item.id} className="history-item">
              <span className={item.ok ? "badge ok" : "badge bad"}>{item.ok ? "OK" : "ERROR"}</span>
              <span>{item.endpoint}</span>
              <span className="muted">{item.ms} ms</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
