import React, { useState, useEffect } from "react";
import "./studio_page.css";
import {
  SpecSummary,
  CreateJobResponse,
} from "@/types/types";
import { fetchCatalog, verifyToolInstalled } from "@/hooks/utils";
import { CatalogExplorer } from "./catalog/catalog_explorer";
import { SpecDetailPanel } from "./catalog/spec_detail_panel";
import { JobCreateModal } from "./modals/job_create_modal";
import { AdvancedJobModal } from "./modals/advanced_job_modal";
import { MediaPreviewModal } from "./modals/media_preview_modal";
import { JobDeck } from "./job_deck/job_deck";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  Plus,
} from "lucide-react";

export const StudioPage: React.FC = () => {
  const toast = useToast();

  const [specs, setSpecs] = useState<SpecSummary[]>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [binaries, setBinaries] = useState<{
    ffmpeg: boolean | null;
    sox: boolean | null;
    magick: boolean | null;
  }>({ ffmpeg: null, sox: null, magick: null });

  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false);
  const [selectedSpec, setSelectedSpec] = useState<SpecSummary | null>(null);

  const [activeJobs, setActiveJobs] = useState<CreateJobResponse[]>([]);

  const [isChoiceModalOpen, setIsChoiceModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAdvancedModalOpen, setIsAdvancedModalOpen] = useState(false);
  const [previewMedia, setPreviewMedia] = useState<{ workdir: string; path: string } | null>(null);

  const initStudio = async () => {
    setLoadingCatalog(true);
    const onResult = (val: any) => null;
    const onError = (val: any) => {if (val) toast.error(val)}
    const [cat, ff, sx, mg] = await Promise.all([
        fetchCatalog(null, (err) => err && toast.error("Erreur catalogue : " + err)),
        verifyToolInstalled("ffmpeg", onResult, onError),
        verifyToolInstalled("sox", onResult, onError),
        verifyToolInstalled("magick", onResult, onError),
    ]);

    if (cat) {
      const allActions = Object.values(cat.action_specs?.all_cat || {});
      const allPipelines = Object.values(cat.pipeline_specs?.all_cat || {});
      setSpecs([...allActions, ...allPipelines]);
    }
    setBinaries({ ffmpeg: ff, sox: sx, magick: mg });
    setLoadingCatalog(false);
  };

  useEffect(() => {
    initStudio();
  }, []);

  const handleLaunchSpec = (spec: SpecSummary) => {
    setSelectedSpec(spec);
    setIsCreateModalOpen(true);
  };

  const handleJobCreated = (newJob: CreateJobResponse) => {
    setActiveJobs((prev) => [newJob, ...prev]);
  };

  const handleRemoveJob = (jobId: string) => {
    setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
  };

  const handleClearAllJobs = () => {
    setActiveJobs([]);
  };

  return (
    <div className="wb-studio-page">
      {/* ─── Barre Haute du Studio ─── */}
      <div className="wb-studio-header">
        <div className="wb-studio-header__left">
          <div className="wb-studio-title-group">
            <h1 className="wb-studio-title">
              Atelier Studio <span className="title-emoji">🛠️</span>
            </h1>
            <span className="wb-studio-subtitle">
              Configurez vos flux CLI multimédia et supervisez vos jobs en direct.
            </span>
          </div>
        </div>

        <div className="wb-studio-header__right">
          <button
            type="button"
            onClick={() => setIsChoiceModalOpen(true)}
            className="wb-btn wb-btn--primary studio-new-job-btn"
          >
            <Plus size={16} />
            <span>Nouveau Job 🚀</span>
          </button>
        </div>
      </div>

      {/* ─── Bandeau HUD / Cockpit Studio ─── */}
      <div className="wb-studio-hud">
        <div className="wb-studio-hud__stat">
          <span className="hud-emoji">🗂️</span>
          <div className="hud-info">
            <span className="hud-value">{specs.length}</span>
            <span className="hud-label">Flux au catalogue</span>
          </div>
        </div>

        <div className="wb-studio-hud__stat">
          <span className="hud-emoji">⚡</span>
          <div className="hud-info">
            <span className="hud-value">{activeJobs.length}</span>
            <span className="hud-label">Jobs en session</span>
          </div>
        </div>

        <div className="wb-studio-hud__stat">
          <span className="hud-emoji">🎬</span>
          <div className="hud-info">
            <span className="hud-value">{binaries.ffmpeg ? "Actif 🟢" : "Absent 🔴"}</span>
            <span className="hud-label">Moteur FFmpeg</span>
          </div>
        </div>

        <div className="wb-studio-hud__stat">
          <span className="hud-emoji">🎚️</span>
          <div className="hud-info">
            <span className="hud-value">{binaries.sox ? "Actif 🟢" : "Absent 🔴"}</span>
            <span className="hud-label">Moteur SoX</span>
          </div>
        </div>

        <div className="wb-studio-hud__stat">
          <span className="hud-emoji">🎨</span>
          <div className="hud-info">
            <span className="hud-value">{binaries.magick ? "Actif 🟢" : "Absent 🔴"}</span>
            <span className="hud-label">Moteur Magick</span>
          </div>
        </div>
      </div>

      {/* ─── Espace de Travail Fluide ─── */}
      <div className="wb-studio-workspace">
        {selectedSpec && (
          <div className="wb-studio-detail-container">
            <SpecDetailPanel
              spec={selectedSpec}
              onClose={() => setSelectedSpec(null)}
              onLaunch={handleLaunchSpec}
            />
          </div>
        )}

        <div className={`wb-studio-catalog-wrapper ${isCatalogCollapsed ? "is-collapsed" : ""}`}>
          <CatalogExplorer
            specs={specs}
            binaries={binaries}
            selectedSpecId={selectedSpec?.id || null}
            onSelectSpec={(spec) => setSelectedSpec(spec)}
            onLaunchSpec={handleLaunchSpec}
            isCollapsed={isCatalogCollapsed}
            onToggleCollapse={() => setIsCatalogCollapsed(!isCatalogCollapsed)}
          />
        </div>
      </div>

      {/* ─── Dock Inférieur pour les N Jobs ─── */}
      <JobDeck
        jobs={activeJobs}
        onRemoveJob={handleRemoveJob}
        onClearAllJobs={handleClearAllJobs}
        onPreviewMedia={(workdir, path) => setPreviewMedia({ workdir, path })}
      />

      {/* ─── MODALES ─── */}
      {isChoiceModalOpen && (
        <div
          className="wb-job-modal-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsChoiceModalOpen(false);
          }}
        >
          <div className="wb-card wb-choice-modal">
            <h3 className="wb-choice-title">Créer un nouveau traitement 🚀</h3>
            <p className="wb-choice-desc">Choisissez votre mode d'exécution :</p>

            <div className="wb-choice-grid">
              <button
                type="button"
                className="wb-choice-card"
                onClick={() => {
                  setIsChoiceModalOpen(false);
                  setIsCatalogCollapsed(false);
                  toast.info("Sélectionnez une action dans le catalogue", { emoji: "👇" });
                }}
              >
                <span className="choice-icon">🗂️</span>
                <h4>Depuis le Catalogue</h4>
                <p>Actions et super-pipelines prédéfinis avec formulaire dynamique sécurisé.</p>
              </button>

              <button
                type="button"
                className="wb-choice-card"
                onClick={() => {
                  setIsChoiceModalOpen(false);
                  setIsAdvancedModalOpen(true);
                }}
              >
                <span className="choice-icon">⚡</span>
                <h4>Mode Manuel (RawEntry)</h4>
                <p>Configurez vous-même les flags, arguments et outils CLI cibles.</p>
              </button>
            </div>
          </div>
        </div>
      )}

      <JobCreateModal
        isOpen={isCreateModalOpen}
        spec={selectedSpec}
        onClose={() => setIsCreateModalOpen(false)}
        onJobCreated={handleJobCreated}
      />

      <AdvancedJobModal
        isOpen={isAdvancedModalOpen}
        onClose={() => setIsAdvancedModalOpen(false)}
        onJobCreated={handleJobCreated}
      />

      <MediaPreviewModal
        workdir={previewMedia?.workdir || null}
        filePath={previewMedia?.path || null}
        onClose={() => setPreviewMedia(null)}
      />
    </div>
  );
};

export default StudioPage;