import { useState } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Simulator from "./pages/Simulator";
import PaymentDetail from "./pages/PaymentDetail";
import { resetDemoData } from "./api";
import "./index.css";

export default function App() {
  const [resetting, setResetting] = useState(false);

  const handleReset = async () => {
    if (!window.confirm("Reset all demo data? This will delete everything and re-seed.")) return;
    setResetting(true);
    try {
      await resetDemoData();
      window.location.reload();
    } catch (e) {
      console.error(e);
      alert("Reset failed — is the backend running?");
    }
    setResetting(false);
  };

  return (
    <BrowserRouter>
      {/* ── SideNavBar (Desktop only) ────────────────────────────── */}
      <nav className="hidden md:flex flex-col bg-white shadow-sm w-64 h-screen fixed left-0 top-0 py-6 gap-4 z-50 border-r border-[#E2E8F0]">
        <div className="px-6 mb-4">
          <h1 className="text-xl font-black text-primary tracking-tight flex items-center gap-1.5">
            <span className="material-symbols-outlined fill-current">bolt</span>
            Clear Horizon
          </h1>
          <p className="text-xs text-slate-500 font-semibold uppercase mt-0.5 tracking-wider">Senior Recovery</p>
        </div>
        
        <div className="flex-1 flex flex-col gap-1 px-4">
          <NavLink 
            to="/" 
            end
            className={({ isActive }) => 
              `flex items-center gap-3 px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all duration-200 ${
                isActive 
                  ? "bg-primary-fixed/80 text-primary border border-primary-fixed" 
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <span className="material-symbols-outlined text-base">dashboard</span>
            Overview
          </NavLink>
          
          <NavLink 
            to="/simulator" 
            className={({ isActive }) => 
              `flex items-center gap-3 px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all duration-200 ${
                isActive 
                  ? "bg-primary-fixed/80 text-primary border border-primary-fixed" 
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`
            }
          >
            <span className="material-symbols-outlined text-base">science</span>
            Simulator
          </NavLink>
        </div>

        <div className="px-4 mt-auto">
          <button 
            className="w-full bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 font-bold text-xs uppercase py-3 rounded-xl transition-colors tracking-wider shadow-sm"
            onClick={handleReset}
            disabled={resetting}
          >
            {resetting ? "Resetting..." : "Reset Demo"}
          </button>
        </div>
      </nav>

      {/* ── TopNavBar (Mobile only) ─────────────────────────────── */}
      <header className="md:hidden flex justify-between items-center px-4 h-16 w-full fixed top-0 bg-white border-b border-[#E2E8F0] z-50 shadow-sm">
        <h1 className="text-lg font-black text-primary flex items-center gap-1">
          <span className="material-symbols-outlined fill-current text-base">bolt</span>
          Clear Horizon
        </h1>
        <div className="flex gap-4">
          <NavLink to="/" end className={({ isActive }) => `text-xs font-bold uppercase tracking-wider ${isActive ? "text-primary" : "text-slate-500"}`}>
            Dashboard
          </NavLink>
          <NavLink to="/simulator" className={({ isActive }) => `text-xs font-bold uppercase tracking-wider ${isActive ? "text-primary" : "text-slate-500"}`}>
            Simulator
          </NavLink>
        </div>
      </header>

      {/* ── Main Content Canvas ─────────────────────────────────── */}
      <main className="flex-1 md:ml-64 p-4 md:p-10 mt-16 md:mt-0 max-w-7xl mx-auto w-full min-h-screen">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/payments/:id" element={<PaymentDetail />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
