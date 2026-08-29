import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";
import "./public/public.css";
import NewVersionBanner from "./components/NewVersionBanner.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <NewVersionBanner />
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);