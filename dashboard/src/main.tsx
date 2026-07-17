import React from "react";
import ReactDOM from "react-dom/client";
import Dashboard from "./Dashboard";
import "./index.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("root element not found");
ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <Dashboard />
  </React.StrictMode>,
);
