import React, { useState, useMemo } from "react";
import "./catalog_explorer.css";
import {
  SpecSummary,
  ActionSummary,
  PipelineSummary,
} from "@/types/types";
import {
  Search,
  SlidersHorizontal,
  Film,
  Music,
  Image as ImageIcon,
  Workflow,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  EyeOff,
  Eye,
  AlertTriangle,
  Play,
  Info,
} from "lucide-react";

export type FilterCategory = "all" | "ffmpeg" | "sox" | "magick" | "pipeline";

interface CatalogExplorerProps {
  specs: SpecSummary[];
  binaries: {
    ffmpeg: boolean | null;
    sox: boolean | null;
    magick: boolean | null;
  };
  selectedSpecId: string | null;
  onSelectSpec: (spec: SpecSummary) => void;
  onLaunchSpec: (spec: SpecSummary) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const CatalogExplorer: React.FC<CatalogExplorerProps> = ({
  specs,
  binaries,
  selectedSpecId,
  onSelectSpec,
  onLaunchSpec,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<FilterCategory>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(12);

  // ─── Vérification des dépendances pour chaque spec ───
  const checkSpecAvailability = (spec: SpecSummary): { isAvailable: boolean; reason?: string } => {
    if (spec.type === "action") {
      const tool = (spec as ActionSummary).tool?.toLowerCase();
      if (tool === "ffmpeg" && binaries.ffmpeg === false) {
        return { isAvailable: false, reason: "FFmpeg manquant" };
      }
      if (tool === "sox" && binaries.sox === false) {
        return { isAvailable: false, reason: "SoX manquant" };
      }
      if ((tool === "magick" || tool === "imagemagick") && binaries.magick === false) {
        return { isAvailable: false, reason: "ImageMagick manquant" };
      }
    } else if (spec.type === "pipeline") {
      const steps = (spec as PipelineSummary).steps || [];
      for (const step of steps) {
        const tool = step.tool?.toLowerCase();
        if (tool === "ffmpeg" && binaries.ffmpeg === false) {
          return { isAvailable: false, reason: "Étape FFmpeg manquante" };
        }
        if (tool === "sox" && binaries.sox === false) {
          return { isAvailable: false, reason: "Étape SoX manquante" };
        }
        if ((tool === "magick" || tool === "imagemagick") && binaries.magick === false) {
          return { isAvailable: false, reason: "Étape ImageMagick manquante" };
        }
      }
    }
    return { isAvailable: true };
  };

  // ─── Filtrage dynamique ───
  const filteredSpecs = useMemo(() => {
    return specs.filter((spec) => {
      // 1. Filtre catégorie
      if (activeCategory === "pipeline" && spec.type !== "pipeline") return false;
      if (activeCategory === "ffmpeg" && (spec.type !== "action" || (spec as ActionSummary).tool !== "ffmpeg"))
        return false;
      if (activeCategory === "sox" && (spec.type !== "action" || (spec as ActionSummary).tool !== "sox"))
        return false;
      if (
        activeCategory === "magick" &&
        (spec.type !== "action" || !["magick", "imagemagick"].includes((spec as ActionSummary).tool))
      )
        return false;

      // 2. Recherche textuelle
      if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase();
        const label = spec.label?.toLowerCase() || "";
        const id = spec.id?.toLowerCase() || "";
        const tool = spec.type === "action" ? (spec as ActionSummary).tool?.toLowerCase() : "pipeline";
        return label.includes(query) || id.includes(query) || tool.includes(query);
      }

      return true;
    });
  }, [specs, activeCategory, searchQuery]);

  // ─── Pagination ───
  const totalPages = Math.ceil(filteredSpecs.length / itemsPerPage) || 1;
  const currentItems = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredSpecs.slice(start, start + itemsPerPage);
  }, [filteredSpecs, currentPage, itemsPerPage]);

  const handleCategoryChange = (cat: FilterCategory) => {
    setActiveCategory(cat);
    setCurrentPage(1);
  };

  // Icône associée à la spec
  const getSpecIcon = (spec: SpecSummary) => {
    if (spec.type === "pipeline") return <Workflow size={16} className="spec-icon spec-icon--pipeline" />;
    const tool = (spec as ActionSummary).tool?.toLowerCase();
    if (tool === "ffmpeg") return <Film size={16} className="spec-icon spec-icon--ffmpeg" />;
    if (tool === "sox") return <Music size={16} className="spec-icon spec-icon--sox" />;
    return <ImageIcon size={16} className="spec-icon spec-icon--magick" />;
  };

  if (isCollapsed) {
    return (
      <div className="wb-catalog-collapsed-bar" onClick={onToggleCollapse} title="Afficher le catalogue">
        <Eye size={16} />
        <span>Afficher le Catalogue des Outils 🗂️</span>
      </div>
    );
  }

  return (
    <div className="wb-catalog-container">
      {/* ─── Barre Haute : Recherche & Contrôle ─── */}
      <div className="wb-catalog-topbar">
        <div className="wb-catalog-search">
          <input
            type="text"
            placeholder="Rechercher une action, codec, filtre (ex: crf, mp3, crop)..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="wb-input wb-catalog-search-input"
          />
        </div>

        <button
          type="button"
          onClick={onToggleCollapse}
          className="wb-btn wb-btn--ghost wb-catalog-collapse-btn"
          title="Masquer le catalogue pour agrandir l'espace de travail"
        >
          <EyeOff size={15} />
          <span>Masquer</span>
        </button>
      </div>

      {/* ─── Filtres d'Outils (Désactivés si binaire absent) ─── */}
      <div className="wb-catalog-filters">
        <button
          type="button"
          className={`wb-catalog-filter-btn ${activeCategory === "all" ? "active" : ""}`}
          onClick={() => handleCategoryChange("all")}
        >
          Tous les flux ({specs.length})
        </button>

        <button
          type="button"
          disabled={binaries.ffmpeg === false}
          className={`wb-catalog-filter-btn ${activeCategory === "ffmpeg" ? "active" : ""}`}
          onClick={() => handleCategoryChange("ffmpeg")}
          title={binaries.ffmpeg === false ? "FFmpeg non disponible sur la machine" : ""}
        >
          <Film size={13} />
          <span>FFmpeg {binaries.ffmpeg === false ? "🔴" : "🎬"}</span>
        </button>

        <button
          type="button"
          disabled={binaries.sox === false}
          className={`wb-catalog-filter-btn ${activeCategory === "sox" ? "active" : ""}`}
          onClick={() => handleCategoryChange("sox")}
          title={binaries.sox === false ? "SoX non disponible sur la machine" : ""}
        >
          <Music size={13} />
          <span>SoX {binaries.sox === false ? "🔴" : "🎚️"}</span>
        </button>

        <button
          type="button"
          disabled={binaries.magick === false}
          className={`wb-catalog-filter-btn ${activeCategory === "magick" ? "active" : ""}`}
          onClick={() => handleCategoryChange("magick")}
          title={binaries.magick === false ? "ImageMagick non disponible sur la machine" : ""}
        >
          <ImageIcon size={13} />
          <span>ImageMagick {binaries.magick === false ? "🔴" : "🎨"}</span>
        </button>

        <button
          type="button"
          className={`wb-catalog-filter-btn ${activeCategory === "pipeline" ? "active" : ""}`}
          onClick={() => handleCategoryChange("pipeline")}
        >
          <Workflow size={13} />
          <span>Super-Pipelines ⚡</span>
        </button>
      </div>

      {/* ─── Grille des Cartes du Catalogue ─── */}
      <div className="wb-catalog-grid">
        {currentItems.length === 0 ? (
          <div className="wb-catalog-empty">
            <AlertTriangle size={24} className="wb-catalog-empty-icon" />
            <p>Aucune action ou pipeline ne correspond à votre recherche.</p>
          </div>
        ) : (
          currentItems.map((spec) => {
            const { isAvailable, reason } = checkSpecAvailability(spec);
            const isSelected = selectedSpecId === spec.id;

            return (
              <div
                key={spec.id}
                className={`wb-card wb-catalog-card ${isSelected ? "is-selected" : ""} ${
                  !isAvailable ? "is-disabled" : ""
                }`}
                onClick={() => onSelectSpec(spec)}
              >
                <div className="wb-catalog-card__header">
                  <div className="wb-catalog-card__icon-wrap">{getSpecIcon(spec)}</div>
                  <span
                    className={`wb-badge ${
                      spec.type === "pipeline" ? "wb-badge--accent" : "wb-badge--info"
                    }`}
                  >
                    {spec.type === "pipeline" ? "Pipeline" : (spec as ActionSummary).tool}
                  </span>
                </div>

                <div className="wb-catalog-card__content">
                  <h4 className="wb-catalog-card__title">{spec.label || spec.id}</h4>
                  <span className="wb-catalog-card__id">{spec.id}</span>
                </div>

                {!isAvailable && (
                  <div className="wb-catalog-card__unavailable">
                    <AlertTriangle size={12} />
                    <span>{reason}</span>
                  </div>
                )}

                <div className="wb-catalog-card__actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className="wb-btn wb-btn--ghost wb-catalog-card__btn-detail"
                    onClick={() => onSelectSpec(spec)}
                  >
                    <Info size={13} />
                    <span>Détails</span>
                  </button>

                  <button
                    type="button"
                    disabled={!isAvailable}
                    className="wb-btn wb-btn--primary wb-catalog-card__btn-launch"
                    onClick={() => onLaunchSpec(spec)}
                  >
                    <Play size={12} fill="currentColor" />
                    <span>Exécuter ⚡</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ─── Pagination & Nombre d'éléments ─── */}
      <div className="wb-catalog-footer">
        <div className="wb-catalog-pagination-info">
          <span>{filteredSpecs.length} action(s) disponible(s)</span>
        </div>

        <div className="wb-catalog-pagination-controls">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="wb-btn wb-btn--ghost wb-catalog-page-btn"
          >
            <ChevronLeft size={16} />
          </button>

          <span className="wb-catalog-page-indicator">
            Page {currentPage} / {totalPages}
          </span>

          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            className="wb-btn wb-btn--ghost wb-catalog-page-btn"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="wb-catalog-per-page">
          <span className="wb-catalog-per-page-label">Par page :</span>
          <input
            type="number"
            min={1}
            max={100}
            value={itemsPerPage}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              setItemsPerPage(isNaN(val) || val < 1 ? 1 : Math.min(val, 100));
              setCurrentPage(1);
            }}
            className="wb-input wb-catalog-per-page-input"
          />
        </div>
      </div>
    </div>
  );
};