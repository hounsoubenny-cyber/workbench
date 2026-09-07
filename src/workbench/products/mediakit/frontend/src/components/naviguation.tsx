import "./naviguation.css";
import React, { useState, useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import {
  Menu,
  X,
  Sliders,
  HelpCircle,
  Home as HomeIcon,
  PanelLeftClose,
  PanelLeftOpen,
  Layers,
  Sparkles,
  Info,
  Wrench,
} from "lucide-react";

// Pages
import Home from "./home";
import ConfigPage from "./config/config_page";
import ConfigModal from "./config/config_modal";
import { verifyToolInstalled } from "@/hooks/utils";
import { useToast } from "./utils/toast/toast_context";
import StudioPage from "./studio/studio_page";
import NotFound from "./not_found/not_found";
import HelpPage from "./help/help";
import { AppConfig } from "@/types/types";
import { getConfig } from "@/hooks/get_config";

export function Naviguation() {
  const toast = useToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [config, setConfig] = useState<AppConfig | null>(null);

  let productName = (config?.productName || "Mediakit");
  productName = productName.split(" ").length > 1 ? productName.split(" ").slice(1).join(" ") : productName
  let version = config?.version || "1.0.0";

  // État de santé des 3 binaires CLI
  const [binaries, setBinaries] = useState<{
    ffmpeg: boolean | null;
    sox: boolean | null;
    magick: boolean | null;
  }>({
    ffmpeg: null,
    sox: null,
    magick: null,
  });

  const location = useLocation();

  useEffect(() => {
    async function init() {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
      } catch (err) {
        console.error("Erreur chargement config.json :", err);
      }
    }
    init();
  }, []);

  // Ferme le menu mobile lors d'un changement de route
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Vérification de la disponibilité des binaires au montage
  useEffect(() => {
    async function checkHealth() {
      const onResult = (val: any) => null;
      const onError = (val: any) => {if (val) toast.error(val)}

      const [ff, sx, mg] = await Promise.all([
        verifyToolInstalled("ffmpeg", onResult, onError),
        verifyToolInstalled("sox", onResult, onError),
        verifyToolInstalled("magick", onResult, onError),
      ]);
      setBinaries({ ffmpeg: ff, sox: sx, magick: mg });
    }
    checkHealth();
  }, []);

  const toggleMenu = () => setMenuOpen(!menuOpen);
  const toggleCollapse = () => setIsCollapsed(!isCollapsed);

  return (
    <div className="nav-container">
      {/* Bouton burger pour mobile */}
      <button className="burger-btn" onClick={toggleMenu} aria-label="Menu principal">
        {menuOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Overlay sombre pour mobile */}
      {menuOpen && <div className="nav-overlay" onClick={toggleMenu} />}

      {/* Barre de navigation latérale */}
      <nav className={`vertical-nav ${menuOpen ? "open" : ""} ${isCollapsed ? "collapsed" : ""}`}>
        {/* ─── En-tête : Logo & Marque ─── */}
        <div className="nav-header">
          <Link to="/" className="nav-logo-link">
            <div className="nav-logo-icon-wrapper">
              <Wrench className="logo-icon" size={20} />
            </div>
            {!isCollapsed && (
              <div className="nav-logo-text-group">
                <span className="logo-brand">Workbench</span>
                <span className="logo-product">
                  {productName} <span className="logo-badge">v{version}</span>
                </span>
              </div>
            )}
          </Link>
        </div>

        {/* ─── Menu des Liens Principaux ─── */}
        <ul className="nav-menu">
          {/* 1. Présentation / Accueil */}
          <li>
            <Link
              to="/"
              className={`nav-link ${location.pathname === "/" ? "active" : ""}`}
            >
              <HomeIcon size={20} className="nav-icon" />
              {!isCollapsed && <span className="nav-name">Acceuil</span>}
              {isCollapsed && <span className="nav-tooltip">Acceuil</span>}
            </Link>
          </li>

          {/* 2.  L'Atelier (Studio principal) */}
          <li>
            <Link
              to="/work"
              className={`nav-link ${location.pathname === "/work" ? "active" : ""}`}
            >
              <Layers size={20} className="nav-icon" />
              {!isCollapsed && <span className="nav-name">Atelier Studio</span>}
              {!isCollapsed && <span className="nav-item-badge">Principal</span>}
              {isCollapsed && <span className="nav-tooltip">Atelier (Studio)</span>}
            </Link>
          </li>

          {/* 3. Page Configuration */}
          <li>
            <Link
              to="/config"
              className={`nav-link ${location.pathname === "/config" ? "active" : ""}`}
            >
              <Sliders size={20} className="nav-icon" />
              {!isCollapsed && <span className="nav-name">Paramètres</span>}
              {isCollapsed && <span className="nav-tooltip">Paramètres Moteur</span>}
            </Link>
          </li>

          {/* 4. Aide & Documentation */}
          <li>
            <Link
              to="/help"
              className={`nav-link ${location.pathname === "/help" ? "active" : ""}`}
            >
              <HelpCircle size={20} className="nav-icon" />
              {!isCollapsed && <span className="nav-name">Aide & Formats</span>}
              {isCollapsed && <span className="nav-tooltip">Aide & Formats</span>}
            </Link>
          </li>
        </ul>

        {/* ─── Pied de navigation ─── */}
        <div className="nav-footer">
          {/* Raccourci Modal Config rapide */}
          <button
            type="button"
            className="nav-quick-modal-btn"
            onClick={() => setIsConfigModalOpen(true)}
            title="Ouvrir la configuration rapide"
          >
            <Sparkles size={16} />
            {!isCollapsed && <span>Config Rapide ⚙️</span>}
          </button>

          {/* Santé des binaires CLI */}
          <div className="nav-binaries-status" title="Disponibilité des exécutables CLI">
            <div className="nav-binaries-title">
              {!isCollapsed && <span>Moteurs CLI :</span>}
            </div>
            <div className="nav-binaries-badges">
              <span
                className={`binary-pill ${
                  binaries.ffmpeg ? "is-online" : binaries.ffmpeg === false ? "is-offline" : ""
                }`}
                title={`FFmpeg : ${binaries.ffmpeg ? "Détecté" : "Non installé"}`}
              >
                FFmpeg {binaries.ffmpeg ? "🟢" : "🔴"}
              </span>

              <span
                className={`binary-pill ${
                  binaries.sox ? "is-online" : binaries.sox === false ? "is-offline" : ""
                }`}
                title={`SoX : ${binaries.sox ? "Détecté" : "Non installé"}`}
              >
                SoX {binaries.sox ? "🟢" : "🔴"}
              </span>

              <span
                className={`binary-pill ${
                  binaries.magick ? "is-online" : binaries.magick === false ? "is-offline" : ""
                }`}
                title={`ImageMagick : ${binaries.magick ? "Détecté" : "Non installé"}`}
              >
                Magick {binaries.magick ? "🟢" : "🔴"}
              </span>
            </div>
          </div>

          {/* Bouton Réduire / Agrandir */}
          <button
            type="button"
            className="nav-collapse-btn-footer"
            onClick={toggleCollapse}
            aria-label={isCollapsed ? "Agrandir" : "Réduire"}
            title={isCollapsed ? "Agrandir le menu" : "Réduire le menu"}
          >
            {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            {!isCollapsed && <span>Réduire la barre</span>}
          </button>
        </div>
      </nav>

      {/* ─── Contenu Principal Dynamique (Routes) ─── */}
      <main className={`content-wrapper ${isCollapsed ? "collapsed" : ""}`}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/work" element={<StudioPage />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      {/* ─── Modale Config Rapide ─── */}
      <ConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
      />
    </div>
  );
}

export default Naviguation;