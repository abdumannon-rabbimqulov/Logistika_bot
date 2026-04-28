import React, { useState, useEffect, useRef } from 'react';
import api from './api';
import { useAuth } from './AuthContext';
import {
  Truck,
  Package,
  MapPin,
  Search,
  MessageCircle,
  User,
  Bell,
  Settings,
  Mic,
  X,
  ChevronRight,
  Star,
  Navigation,
  Activity,
  Zap,
  CheckCircle2,
  Layers,
  ArrowRight,
  Filter,
  Sparkles,
  Send,
  BrainCircuit,
  Plus,
  Minus,
  LocateFixed,
  Phone,
  Clock,
  ExternalLink,
  MoreVertical,
  Cpu,
  Orbit,
  CircleDot,
  Navigation2,
  Box,
  CreditCard,
  LogOut,
  ShieldCheck,
  Smartphone,
  Wallet,
  Award,
  Globe,
  Compass,
  History,
  Timer,
  GanttChartSquare,
  HandCoins
} from 'lucide-react';

// --- Konfiguratsiya ---
const apiKey = "";
const appId = typeof __app_id !== 'undefined' ? __app_id : 'logiai-tma-v1';

const COLORS = {
  bg: '#050610',
  glass: 'rgba(255, 255, 255, 0.04)',
  glassBorder: 'rgba(255, 255, 255, 0.08)',
  accent: 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
};

// --- Komponentlar ---
const BrandLogo = () => (
  <div className="flex items-center gap-2.5">
    <div className="relative">
      <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(168,85,247,0.4)]">
        <Cpu size={22} className="text-white" />
      </div>
    </div>
    <div className="flex flex-col leading-none">
      <span className="font-black text-xl tracking-tighter italic text-white">LOGI<span className="text-purple-400 not-italic">AI</span></span>
      <span className="text-[8px] font-bold text-white/40 tracking-[0.2em] uppercase">Logistics Intelligence</span>
    </div>
  </div>
);

const GlassCard = ({ children, className = "", onClick }) => (
  <div
    onClick={onClick}
    className={`backdrop-blur-2xl border rounded-3xl transition-all ${className}`}
    style={{ backgroundColor: COLORS.glass, borderColor: COLORS.glassBorder }}
  >
    {children}
  </div>
);

// --- YO'NALISH VIZUALIZATSIYASI ---
const RouteVisualizer = ({ waypoints }) => {
  const getStatusStyle = (type) => {
    switch(type) {
      case 'PICKUP': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
      case 'DELIVERY': return 'text-rose-400 bg-rose-400/10 border-rose-400/20';
      case 'TRANSIT': return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
      default: return 'text-white/40 bg-white/5 border-white/10';
    }
  };

  const getDotColor = (type) => {
    switch(type) {
      case 'PICKUP': return 'bg-emerald-500';
      case 'DELIVERY': return 'bg-rose-500';
      case 'TRANSIT': return 'bg-amber-500';
      default: return 'bg-white/20';
    }
  };

  return (
    <div className="relative py-2">
      <div className="absolute left-[15px] top-6 bottom-6 w-[2px] bg-white/5" />
      <div className="space-y-6">
        {waypoints.map((wp, idx) => (
          <div key={idx} className="relative flex items-start gap-4">
            <div className="relative z-10 mt-1.5">
               <div className={`w-8 h-8 rounded-full border flex items-center justify-center bg-[#050610] ${getStatusStyle(wp.type).split(' ')[2]}`}>
                  <div className={`w-2.5 h-2.5 rounded-full ${getDotColor(wp.type)} shadow-[0_0_8px_rgba(255,255,255,0.2)]`} />
               </div>
            </div>
            <div className="flex-1">
               <div className="flex items-center justify-between">
                  <p className="text-sm font-black text-white/90 tracking-tight">{wp.address}</p>
                  <span className={`text-[8px] font-black uppercase px-2 py-0.5 rounded-md border tracking-widest ${getStatusStyle(wp.type)}`}>
                    {wp.type}
                  </span>
               </div>
               <p className="text-[10px] text-white/30 font-medium mt-0.5">
                  {wp.type === 'PICKUP' ? 'Yuk ortish manzili' : wp.type === 'DELIVERY' ? 'Yuk tushirish manzili' : 'Vaqtinchalik to\'xtash joyi'}
               </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- 1. LENTA SCREEN ---
const LentaScreen = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const res = await api.get('/orders/');
        // Backend returns array of orders
        setOrders(res.data);
      } catch (err) {
        console.error("Failed to fetch orders", err);
      } finally {
        setLoading(false);
      }
    };
    fetchOrders();
  }, []);

  const handleBook = async (orderId, price) => {
    if (user?.role !== 'DRIVER') {
      alert("Faqat haydovchilar yuk band qilishi mumkin");
      return;
    }
    try {
      await api.post(`/orders/${orderId}/offers`, {
        offered_price: price,
        comment: "Tezda olib ketaman"
      });
      window.Telegram?.WebApp?.showAlert("Muvaffaqiyatli band qilindi!");
    } catch (err) {
      console.error("Booking error:", err);
      alert("Xatolik yuz berdi");
    }
  };

  const handleOffer = async (orderId) => {
    if (user?.role !== 'DRIVER') {
      alert("Faqat haydovchilar taklif bera oladi");
      return;
    }
    const price = prompt("O'z narxingizni kiriting:");
    if (!price) return;
    try {
      await api.post(`/orders/${orderId}/offers`, {
        offered_price: parseInt(price),
        comment: "Mening taklifim"
      });
      window.Telegram?.WebApp?.showAlert("Taklif yuborildi!");
    } catch (err) {
      console.error("Offer error:", err);
      alert("Xatolik yuz berdi");
    }
  };

  return (
    <div className="px-5 pt-4 pb-32 space-y-4 overflow-y-auto h-full no-scrollbar">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-2xl font-black tracking-tight">Yangi Yuklar</h2>
          <p className="text-[10px] text-white/30 font-bold uppercase tracking-widest mt-1 italic">Jonli efir: {orders.length} ta faol e'lon</p>
        </div>
        <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-white/60"><Filter size={20}/></button>
      </div>

      {loading ? (
         <div className="flex justify-center p-10"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>
      ) : orders.length === 0 ? (
         <div className="text-center p-10 text-white/40">Hozircha yangi yuklar yo'q</div>
      ) : (
        orders.map(order => (
          <GlassCard key={order.id} className="p-6 group border-white/5 hover:border-purple-500/30">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center text-purple-400 border border-purple-500/10 shadow-inner">
                  <Box size={28} />
                </div>
                <div>
                  <h3 className="font-black text-lg tracking-tight">{order.cargo_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[9px] uppercase tracking-widest font-black text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded border border-purple-400/20">Yuk turi ID: {order.required_truck_type_id}</span>
                    <span className="text-[9px] uppercase tracking-widest font-black text-white/30">{order.weight} Tonna</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-emerald-400 font-black text-2xl tracking-tighter">
                  {new Intl.NumberFormat('uz-UZ').format(order.price)}
                </p>
                <p className="text-[9px] opacity-40 uppercase font-black tracking-widest">{order.currency}</p>
              </div>
            </div>

            <div className="mb-6 px-1">
              <RouteVisualizer waypoints={(order.waypoints || []).map(wp => ({
                address: wp.city + (wp.address ? `, ${wp.address}` : ''),
                type: wp.waypoint_type.toUpperCase()
              }))} />
            </div>

            <div className="flex gap-3 mt-4">
              <button 
                onClick={() => handleBook(order.id, order.price)}
                className="flex-[2.5] py-4 rounded-2xl bg-white text-black font-black text-sm active:scale-95 transition-all shadow-[0_10px_20px_rgba(255,255,255,0.1)] uppercase tracking-tighter"
              >
                Band qilish
              </button>
              <button 
                onClick={() => handleOffer(order.id)}
                className="flex-1 py-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center gap-2 text-white/80 font-black text-[11px] active:scale-95 transition-all uppercase tracking-tighter hover:bg-white/10"
              >
                <HandCoins size={18} className="text-purple-400" />
                Taklif
              </button>
            </div>
          </GlassCard>
        ))
      )}
    </div>
  );
};


// --- 2. XARITA SCREEN ---
const MapScreen = () => {
  const [selectedPin, setSelectedPin] = useState(null);
  const [pins, setPins] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPins = async () => {
      try {
        const res = await api.get('/orders/');
        const mappedPins = res.data.map(order => ({
          id: order.id,
          // If backend has latitude/longitude, map them to %
          // For now, random positions that look realistic for the mock map
          x: Math.floor(Math.random() * 80) + 10,
          y: Math.floor(Math.random() * 60) + 20,
          price: (order.price / 1000000).toFixed(1) + 'M',
          cargo: order.cargo_name,
          from: order.waypoints?.[0]?.city || 'Noma\'lum',
          to: order.waypoints?.[order.waypoints.length - 1]?.city || 'Noma\'lum',
          profit: order.price > 5000000 ? 'Premium' : 'Normal',
          eta: "Ko'rish"
        }));
        setPins(mappedPins);
      } catch (err) {
        console.error("Failed to fetch pins", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPins();
  }, []);

  return (
    <div className="relative h-full w-full bg-[#080a15] overflow-hidden">
      <div className="absolute inset-0 z-0 opacity-10" style={{ backgroundImage: `radial-gradient(circle, #ffffff 1px, transparent 1px)`, backgroundSize: '30px 30px' }} />

      <div className="absolute top-6 left-5 right-5 z-30">
        <GlassCard className="flex items-center gap-3 px-4 py-3 border-white/10 shadow-2xl">
          <Search size={18} className="text-white/40" />
          <input className="bg-transparent border-none outline-none text-xs w-full placeholder-white/20" placeholder="Shahar yoki yuk izlash..." />
        </GlassCard>
      </div>

      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : pins.map(pin => (
        <div key={pin.id} className="absolute z-20" style={{ left: `${pin.x}%`, top: `${pin.y}%` }}>
          <div onClick={() => setSelectedPin(pin)} className="flex flex-col items-center group cursor-pointer transition-transform active:scale-90">
            <div className={`px-2 py-1 rounded-lg text-[9px] font-black mb-1 transition-all ${selectedPin?.id === pin.id ? 'bg-purple-600 shadow-[0_0_15px_rgba(168,85,247,0.5)]' : 'bg-black/80 border border-white/20 text-purple-400'}`}>{pin.price}</div>
            <div className={`w-6 h-6 rounded-lg rotate-45 flex items-center justify-center transition-all ${selectedPin?.id === pin.id ? 'bg-white text-purple-600' : 'bg-purple-600 text-white'}`}>
              <Navigation2 size={12} className="-rotate-45" />
            </div>
          </div>
        </div>
      ))}

      {selectedPin && (
        <div className="absolute bottom-32 left-5 right-5 z-40 animate-in slide-in-from-bottom">
          <GlassCard className="p-5 border-purple-500/40 shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
            <div className="flex justify-between items-start mb-4">
               <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles size={14} className="text-yellow-500" />
                    <span className="text-[9px] font-black uppercase text-yellow-500 tracking-widest">{selectedPin.profit} Taklif</span>
                  </div>
                  <h3 className="font-black text-lg">{selectedPin.from} → {selectedPin.to}</h3>
                  <p className="text-[10px] text-white/40">{selectedPin.cargo} • {selectedPin.eta}</p>
               </div>
               <button onClick={() => setSelectedPin(null)} className="p-2 text-white/20"><X size={18}/></button>
            </div>
            <div className="flex gap-2">
               <button className="flex-1 py-4 bg-white text-black font-black text-xs rounded-2xl uppercase tracking-tighter">Band qilish</button>
               <button className="px-5 bg-white/5 border border-white/10 rounded-2xl text-white"><Navigation size={18}/></button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

// --- 3. YUKLARIM SCREEN (BOYITILGAN VERSIYA QAYTARILDI) ---
const MyOrdersScreen = () => {
  const { user } = useAuth();
  const [view, setView] = useState('active');
  const [myOrders, setMyOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMyOrders = async () => {
      try {
        if (!user) return;
        const endpoint = user.role === 'DRIVER' 
          ? `/orders/?driver_id=${user.id}` 
          : `/orders/?customer_id=${user.id}`;
        
        const res = await api.get(endpoint);
        setMyOrders(res.data);
      } catch (err) {
        console.error("Failed to fetch my orders", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMyOrders();
  }, [user]);
  return (
    <div className="px-5 pt-4 pb-32 h-full overflow-y-auto no-scrollbar space-y-6">
      <div className="flex flex-col gap-5">
        <div className="flex justify-between items-end">
          <h2 className="text-2xl font-black tracking-tight">Mening Safarlarim</h2>
          <span className="text-[10px] font-black text-purple-500 uppercase tracking-widest bg-purple-500/10 px-3 py-1 rounded-full border border-purple-500/20">{myOrders.length} ta</span>
        </div>

        <div className="flex gap-2 p-1.5 bg-white/5 rounded-2xl border border-white/10">
          {['active', 'completed', 'history'].map(v => (
            <button key={v} onClick={() => setView(v)} className={`flex-1 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all ${view === v ? 'bg-white text-black shadow-lg' : 'text-white/30'}`}>
              {v === 'active' ? 'Faol' : v === 'completed' ? 'Tugallangan' : 'Tarix'}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {loading ? (
          <div className="flex justify-center p-10"><div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div></div>
        ) : myOrders.length === 0 ? (
          <div className="text-center p-10 text-white/40">Hozircha safarlar yo'q</div>
        ) : (
          myOrders.map(order => (
            <GlassCard key={order.id} className="p-0 overflow-hidden border-white/5 group">
              <div className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                      <span className="text-[9px] font-black text-white/40 uppercase tracking-widest">LOG-{order.id}</span>
                    </div>
                    <h3 className="text-lg font-black">{order.cargo_name}</h3>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-black text-emerald-400">
                      {new Intl.NumberFormat('uz-UZ').format(order.price)}<span className="text-[10px] opacity-40 ml-1"></span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-2xl border border-white/5 mb-5">
                  <div className="flex-1">
                    <p className="text-[8px] opacity-30 font-black uppercase mb-1">A' nuqta</p>
                    <p className="text-xs font-bold truncate">{order.waypoints?.[0]?.city || 'Noma\'lum'}</p>
                  </div>
                  <Truck size={14} className="text-purple-400" />
                  <div className="flex-1 text-right">
                    <p className="text-[8px] opacity-30 font-black uppercase mb-1">B' nuqta</p>
                    <p className="text-xs font-bold truncate">{order.waypoints?.[order.waypoints.length - 1]?.city || 'Noma\'lum'}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                     <div className="flex items-center gap-3">
                        <div className="flex flex-col">
                           <span className="text-[8px] opacity-30 font-black uppercase">Status</span>
                           <span className="text-xs font-black">{order.status}</span>
                        </div>
                     </div>
                     <span className="text-[10px] font-black text-purple-400">Yo'lda</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-purple-600 to-indigo-500 shadow-[0_0_15px_rgba(168,85,247,0.5)]" style={{ width: `50%` }} />
                  </div>
                </div>
              </div>
              <button className="w-full py-4 bg-white/5 border-t border-white/5 text-[10px] font-black uppercase tracking-widest text-white/40 active:bg-white/10 transition-colors">
                Safar tafsilotlari
              </button>
            </GlassCard>
          ))
        )}
      </div>
    </div>
  );
};

// --- 4. PROFIL SCREEN ---
const ProfileScreen = () => {
  const { user } = useAuth();

  return (
    <div className="px-5 pt-4 pb-32 h-full overflow-y-auto no-scrollbar text-center space-y-6">
      <div className="pt-6">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-tr from-purple-600 to-indigo-600 mx-auto mb-4 flex items-center justify-center p-1 shadow-2xl">
          <div className="w-full h-full bg-[#050610] rounded-[1.4rem] flex items-center justify-center overflow-hidden">
            <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.full_name || 'Felix'}`} alt="Avatar" className="w-20" />
          </div>
        </div>
        <h2 className="text-2xl font-black tracking-tight">{user?.full_name || 'Foydalanuvchi'}</h2>
        <p className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em] mt-1 italic">{user?.role || 'Guest'}</p>
        <p className="text-sm font-bold text-white/60 mt-2">{user?.phone_number || 'Raqam kiritilmagan'}</p>
      </div>

      <GlassCard className="p-6 bg-gradient-to-br from-indigo-600 to-purple-700 border-none shadow-2xl relative overflow-hidden text-left">
        <div className="relative z-10">
          <p className="text-white/60 text-[10px] font-black uppercase tracking-widest">Mening Balansim</p>
          <h3 className="text-3xl font-black mt-1">4,250,000 <span className="text-sm font-bold opacity-60">UZS</span></h3>
          <div className="flex gap-2 mt-4">
             <button className="flex-1 py-3 bg-white text-indigo-600 rounded-xl font-black text-[10px] uppercase tracking-wider active:scale-95 transition-all">To'ldirish</button>
             <button className="flex-1 py-3 bg-black/20 text-white rounded-xl font-black text-[10px] uppercase tracking-wider active:scale-95 transition-all border border-white/10">Yechish</button>
          </div>
        </div>
        <div className="absolute -right-4 -bottom-4 opacity-10 rotate-12"><Wallet size={120} /></div>
      </GlassCard>

      <div className="space-y-2">
        {[
          { icon: ShieldCheck, label: "Xavfsizlik & Hujjatlar", color: "text-green-400" },
          { icon: Smartphone, label: "Ilova sozlamalari", color: "text-blue-400" },
          { icon: History, label: "Tranzaksiyalar tarixi", color: "text-amber-400" },
          { icon: LogOut, label: "Chiqish", color: "text-red-400" }
        ].map((item, i) => (
          <button key={i} className="w-full p-4 flex items-center justify-between rounded-2xl bg-white/5 border border-transparent active:border-white/10 transition-all group">
            <div className="flex items-center gap-4 text-sm font-bold text-white/80">
               <item.icon size={20} className={`${item.color} group-hover:scale-110 transition-transform`} />
               {item.label}
            </div>
            <ChevronRight size={18} className="text-white/10" />
          </button>
        ))}
      </div>
    </div>
  );
};

// --- RO'L TANLASH SCREEN ---
const RoleSelectionScreen = () => {
  const { selectRole } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSelect = async (role) => {
    setLoading(true);
    await selectRole(role);
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-[#050610] text-white font-sans flex flex-col items-center justify-center p-6 z-[100]">
      <div className="mb-10 text-center">
        <BrandLogo />
        <h2 className="text-2xl font-black mt-8">Xush kelibsiz!</h2>
        <p className="text-white/40 text-sm mt-2">Ilovadan foydalanish uchun o'z rolingizni tanlang</p>
      </div>

      <div className="w-full max-w-sm space-y-4">
        <button 
          onClick={() => handleSelect('driver')}
          disabled={loading}
          className="w-full p-6 rounded-3xl bg-gradient-to-tr from-purple-600/20 to-indigo-600/20 border border-purple-500/30 flex items-center gap-4 active:scale-95 transition-all hover:bg-purple-500/20"
        >
          <div className="w-14 h-14 rounded-2xl bg-purple-500/20 flex items-center justify-center text-purple-400">
            <Truck size={28} />
          </div>
          <div className="text-left">
            <h3 className="text-lg font-black">Haydovchi</h3>
            <p className="text-xs text-white/40 mt-1">Yuk tashish va pul ishlash</p>
          </div>
        </button>

        <button 
          onClick={() => handleSelect('sender')}
          disabled={loading}
          className="w-full p-6 rounded-3xl bg-white/5 border border-white/10 flex items-center gap-4 active:scale-95 transition-all hover:bg-white/10"
        >
          <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center text-white/80">
            <Package size={28} />
          </div>
          <div className="text-left">
            <h3 className="text-lg font-black">Yuk Egasi (Sender)</h3>
            <p className="text-xs text-white/40 mt-1">Yuk yuborish va haydovchi topish</p>
          </div>
        </button>
      </div>

      {loading && (
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}
    </div>
  );
};

// --- ASOSIY ILOVA ---
export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const { user, loading, needsRoleSelection } = useAuth();

  if (loading) {
    return (
      <div className="fixed inset-0 bg-[#050610] flex items-center justify-center flex-col gap-4">
        <BrandLogo />
        <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mt-4"></div>
      </div>
    );
  }

  if (needsRoleSelection) {
    return <RoleSelectionScreen />;
  }

  return (
    <div className="fixed inset-0 bg-[#050610] text-white font-sans overflow-hidden select-none">
      <header className={`px-5 pt-14 pb-5 flex justify-between items-center relative z-50 ${activeTab === 'map' ? 'bg-transparent' : 'bg-black/20 backdrop-blur-xl border-b border-white/5'}`}>
        <BrandLogo />
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center relative active:scale-90 transition-transform">
            <Bell size={20} className="text-white/60" />
            <div className="absolute top-2.5 right-2.5 w-2 h-2 bg-purple-500 rounded-full border-2 border-[#050610]" />
          </div>
        </div>
      </header>

      <main className="h-full relative overflow-hidden">
        {activeTab === 'home' && <LentaScreen />}
        {activeTab === 'map' && <MapScreen />}
        {activeTab === 'orders' && <MyOrdersScreen />}
        {activeTab === 'profile' && <ProfileScreen />}
      </main>

      <button className="fixed bottom-32 right-6 z-50 w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 shadow-2xl shadow-purple-600/30 flex items-center justify-center active:scale-90 transition-all animate-bounce">
        <Sparkles size={24} />
      </button>

      <nav className="fixed bottom-0 left-0 right-0 z-50 px-6 pb-10 pt-4 bg-gradient-to-t from-black to-transparent">
        <div className="bg-[#121421]/90 backdrop-blur-2xl border border-white/10 rounded-[2rem] p-2 flex items-center justify-between shadow-2xl">
          {[
            { id: 'home', icon: Truck, label: 'Lenta' },
            { id: 'map', icon: Navigation, label: 'Xarita' },
            { id: 'orders', icon: Package, label: 'Safarlar' },
            { id: 'profile', icon: User, label: 'Profil' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center flex-1 py-2 transition-all ${activeTab === tab.id ? 'text-purple-400 scale-105' : 'text-white/30'}`}
            >
              <tab.icon size={22} strokeWidth={activeTab === tab.id ? 2.5 : 2} />
              <span className="text-[9px] font-black mt-1 uppercase tracking-tighter">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; background: #050610; }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .animate-in { animation: slideIn 0.3s ease-out; }
        @keyframes slideIn { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
      `}</style>
    </div>
  );
}