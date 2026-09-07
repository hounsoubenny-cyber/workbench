import React from "react";
import "./not_found.css";
import { Link } from "react-router-dom";
import {
  FileQuestion,
  Layers,
  Home as HomeIcon,
  HelpCircle,
  Terminal,
  ArrowLeft,
} from "lucide-react";

export const NotFound: React.FC = () => {
  return (
    <div className="wb-notfound-container">
      <div className="wb-notfound-card">
        {/* Badge d'erreur */}
        <div className="wb-notfound-badge">
          <span className="badge-emoji">📡</span>
          <span>ERREUR 404 · CHEMIN INTROUVABLE</span>
        </div>

        {/* Chiffre 404 avec halo stylé */}
        <h1 className="wb-notfound-code">404</h1>

        <h2 className="wb-notfound-title">Flux ou Route Inexistante</h2>
        <p className="wb-notfound-desc">
          L'adresse demandée ne correspond à aucune route de l'application ni à aucun pipeline multimédia déclaré.
        </p>

        {/* Bloc console d'erreur CLI simulé */}
        <div className="wb-notfound-terminal">
          <div className="wb-notfound-terminal__header">
            <Terminal size={13} />
            <span>workbench-engine.log</span>
          </div>
          <div className="wb-notfound-terminal__body">
            <span className="log-line line-err">
              [CRITICAL] RouteNotFound: Target URL does not match any registered spec or page.
            </span>
            <span className="log-line line-dim">
              [STATUS] Subprocess exited with return code 1.
            </span>
            <span className="log-line line-info">
              [HINT] Try navigating back to the Studio workspace or check the catalog.
            </span>
          </div>
        </div>

        {/* Boutons de redirection */}
        <div className="wb-notfound-actions">
          <Link to="/work" className="wb-btn wb-btn--primary notfound-btn">
            <Layers size={16} />
            <span>Aller à l'Atelier Studio 🛠️</span>
          </Link>

          <Link to="/" className="wb-btn wb-btn--ghost notfound-btn">
            <HomeIcon size={16} />
            <span>Accueil 🏠</span>
          </Link>

          <Link to="/help" className="wb-btn wb-btn--ghost notfound-btn">
            <HelpCircle size={16} />
            <span>Consulter l'Aide 📖</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFound;