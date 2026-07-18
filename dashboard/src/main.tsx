import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./Dashboard";
import BacktestReport from "./browse/BacktestReport";
import AnalyzePage from "./browse/AnalyzePage";
import "./index.css";

/* wrapper that passes initialTab to Dashboard */
function BrowsePage() {
  return <Dashboard initialTab="browse" />;
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("root element not found");

createRoot(rootEl).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/browse" element={<BrowsePage />} />
        <Route path="/backtest/:id" element={<BacktestReport />} />
        <Route path="/analyze" element={<AnalyzePage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
