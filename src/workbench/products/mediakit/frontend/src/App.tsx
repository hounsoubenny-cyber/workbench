import { useEffect, useState } from "react";
import { BrowserRouter } from "react-router-dom";
import Naviguation from "./components/naviguation";
import { getConfig } from "./hooks/get_config";
import { AppConfig } from "./types/types";
import { ToastProvider } from "@/components/utils/toast/toast_context"; 
import ThemeSelector, {
  applyTheme,
  getStoredTheme,
} from "./components/theme_selector/theme_selector";

export function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // 1. Initialisation du thème avant tout rendu
  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);

  // 2. Chargement de la configuration initiale (/config.json)
  useEffect(() => {
    async function init() {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
      } catch (err) {
        console.error("Erreur chargement config.json :", err);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  // Écran d'attente minimaliste pendant la lecture de config.json
  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "12px",
          background: "var(--bg-app)",
          color: "var(--text-secondary)",
          fontFamily: "var(--font-mono)",
          fontSize: "0.9rem",
        }}
      >
        <span style={{ fontSize: "1.8rem" }}>⚙️</span>
        <span>Chargement de Workbench Mediakit...</span>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <ToastProvider>
        <div className="wb-app">
          {/* Sélecteur de thème flottant en bas à droite */}
          <ThemeSelector />

          {/* Barre de navigation + Contenu des routes */}
          <Naviguation />
        </div>
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;