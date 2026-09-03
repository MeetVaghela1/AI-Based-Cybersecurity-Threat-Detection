import React, { useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Compare from "./pages/Compare.jsx";
import HowItWorks from "./pages/HowItWorks.jsx";
import Database from "./pages/Database.jsx";
import OnboardingTour from "./components/OnboardingTour.jsx";
import { MonitorProvider } from "./components/MonitorContext.jsx";

const TABS = [
  { id: "monitor", label: "Live Monitor" },
  { id: "compare", label: "Model Comparison" },
  { id: "database", label: "Database" },
  { id: "learn", label: "How It Works" },
];

function AppInner() {
  const [tab, setTab] = useState("monitor");
  const [tourOpen, setTourOpen] = useState(true);

  const launchTour = () => setTourOpen(true);

  const finishTour = () => setTourOpen(false);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-dot" />
          <span className="brand-name">CyberGuard</span>
          <span className="brand-sub">AI-based threat detection</span>
        </div>
        <nav className="nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-btn ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        {!tourOpen && (
          <button className="ghost tour-btn" onClick={launchTour}>
            Take the tour
          </button>
        )}
        <span className="badge-live">SIMULATED TRAFFIC</span>
      </header>

      <main className="content">
        {tab === "monitor" && <Dashboard onStartTour={launchTour} />}
        {tab === "compare" && <Compare />}
        {tab === "database" && <Database />}
        {tab === "learn" && <HowItWorks />}
      </main>

      <footer className="footer">
        Demonstrating ML-based intrusion detection on recorded NSL-KDD &amp;
        CICIDS2017 dataset traffic. Educational project — not a live intrusion tool.
      </footer>

      <OnboardingTour
        tab={tab}
        setTab={setTab}
        visible={tourOpen}
        onFinish={finishTour}
      />
    </div>
  );
}

export default function App() {
  return (
    <MonitorProvider>
      <AppInner />
    </MonitorProvider>
  );
}
