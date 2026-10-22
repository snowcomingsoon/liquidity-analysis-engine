import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { useLang } from "./lib/i18n";
import "./index.css";

// A new language redraws the whole app: texts built once (labels, lists) read it again.
function Root() { return <App key={useLang()} />; }

createRoot(document.getElementById("root")!).render(<StrictMode><Root /></StrictMode>);
