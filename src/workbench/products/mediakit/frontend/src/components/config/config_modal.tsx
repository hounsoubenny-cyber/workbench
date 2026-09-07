import React, { useState, useEffect, useRef } from "react";
import "./config_modal.css";
import { WbConfig } from "@/types/types";
import { fetchServerConfig, updateServerConfig } from "@/hooks/utils";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  X,
  Sliders,
  Save,
  RotateCcw,
  Cpu,
  Clock,
  HardDrive,
  Terminal,
  RefreshCw,
  Sparkles,
  Zap,
  AlertCircle,
} from "lucide-react";

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: (newConfig: WbConfig) => void;
}

const formatDuration = (seconds: number): string => {
  if (!seconds || seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  if (s > 0 || parts.length === 0) parts.push(`${s}s`);
  return parts.join(" ");
};

export const ConfigModal: React.FC<ConfigModalProps> = ({
  isOpen,
  onClose,
  onUpdated,
}) => {
  const toast = useToast();
  const modalRef = useRef<HTMLDivElement>(null);

  const [initialConfig, setInitialConfig] = useState<WbConfig | null>(null);
  const [formData, setFormData] = useState<WbConfig>({
    max_concurrent_job: 10,
    buffer_max_lines: 5000,
    buffer_clear_delay: 120,
    file_ttl: 3600,
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  // Chargement de la config backend à l'ouverture du modal
  const loadConfig = async (silent: boolean = false) => {
    let fetchError: string | null = null;

    const conf = await fetchServerConfig(
      (data) => {
        if (data) {
          setInitialConfig(data);
          setFormData(data);
        }
      },
      (err) => {
        fetchError = err;
      },
      setLoading
    );

    if (fetchError && !silent) {
      toast.error("Erreur de synchronisation", {
        emoji: "📡",
        description: fetchError,
      });
    } else if (conf && silent) {
      toast.success("Paramètres synchronisés !", {
        emoji: "🔄",
      });
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConfig(false);
    }
  }, [isOpen]);

  // Fermeture via touche Échap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Détection des modifications locales
  const isDirty =
    initialConfig !== null &&
    (formData.max_concurrent_job !== initialConfig.max_concurrent_job ||
      formData.buffer_max_lines !== initialConfig.buffer_max_lines ||
      formData.buffer_clear_delay !== initialConfig.buffer_clear_delay ||
      formData.file_ttl !== initialConfig.file_ttl);

  const handleInputChange = (field: keyof WbConfig, rawValue: string) => {
    const num = rawValue === "" ? 0 : parseInt(rawValue, 10);
    setFormData((prev) => ({
      ...prev,
      [field]: isNaN(num) ? 0 : num,
    }));
  };

  const handleReset = () => {
    if (initialConfig) {
      setFormData(initialConfig);
      toast.info("Paramètres rétablis", {
        emoji: "↩️",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty || saving) return;

    let saveError: string | null = null;

    const ok = await updateServerConfig(
      formData,
      null,
      (err) => {
        saveError = err;
      },
      setSaving
    );

    if (ok) {
      setInitialConfig(formData);
      if (onUpdated) onUpdated(formData);
      toast.success("Configuration sauvegardée !", {
        emoji: "✨",
        description: "Appliquée immédiatement sans recharger l'application.",
      });
    } else {
      toast.error("Échec de la sauvegarde", {
        emoji: "💥",
        description: saveError || "Une erreur est survenue côté serveur.",
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="wb-config-modal-overlay"
      onClick={(e) => {
        // Clic en dehors du modal pour fermer
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="wb-config-modal" ref={modalRef}>
        {/* ─── En-tête Modal ─── */}
        <div className="wb-config-modal__header">
          <div className="wb-config-modal__title-group">
            <span className="wb-config-modal__badge">
              <Sliders size={13} />
              <span>Paramètres Rapides ⚙️</span>
            </span>
            <h3 className="wb-config-modal__title">Configuration Système</h3>
          </div>

          <div className="wb-config-modal__header-actions">
            <button
              type="button"
              onClick={() => loadConfig(true)}
              disabled={loading || saving}
              className="wb-btn wb-btn--ghost wb-config-modal__btn-icon"
              title="Rafraîchir depuis le serveur"
            >
              <RefreshCw size={14} className={loading ? "wb-spin" : ""} />
            </button>

            <button
              type="button"
              onClick={onClose}
              className="wb-config-modal__close-btn"
              aria-label="Fermer la boîte de dialogue"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* ─── Corps Scrollable ─── */}
        <form onSubmit={handleSubmit} className="wb-config-modal__form">
          <div className="wb-config-modal__body">
            {/* 1. Concurrence */}
            <div className="wb-config-modal__section">
              <div className="wb-config-modal__field-header">
                <label htmlFor="modal_max_jobs" className="wb-config-modal__label">
                  <Cpu size={14} className="wb-config-modal__label-icon" />
                  <span>Concurrence des jobs simultanés ⚡</span>
                </label>
                <span className="wb-config-modal__pill">
                  <Zap size={11} /> max 64
                </span>
              </div>

              <div className="wb-config-modal__input-row">
                <input
                  id="modal_max_jobs"
                  type="number"
                  min={1}
                  max={64}
                  value={formData.max_concurrent_job}
                  disabled={loading || saving}
                  onChange={(e) => handleInputChange("max_concurrent_job", e.target.value)}
                  className="wb-input wb-config-modal__input"
                />
                <span className="wb-config-modal__unit">tâches CLI 🚀</span>
              </div>
              <span className="wb-config-modal__help">
                Limite le nombre de conversions simultanées (FFmpeg, SoX, Magick).
              </span>
            </div>

            {/* 2. TTL Fichiers */}
            <div className="wb-config-modal__section">
              <div className="wb-config-modal__field-header">
                <label htmlFor="modal_ttl" className="wb-config-modal__label">
                  <HardDrive size={14} className="wb-config-modal__label-icon" />
                  <span>Rétention des fichiers de travail (TTL) 🧹</span>
                </label>
                <span className="wb-config-modal__preview">
                  ⏳ ~ {formatDuration(formData.file_ttl)}
                </span>
              </div>

              <div className="wb-config-modal__input-row">
                <input
                  id="modal_ttl"
                  type="number"
                  min={60}
                  step={60}
                  value={formData.file_ttl}
                  disabled={loading || saving}
                  onChange={(e) => handleInputChange("file_ttl", e.target.value)}
                  className="wb-input wb-config-modal__input"
                />
                <span className="wb-config-modal__unit">secondes ⏱️</span>
              </div>
              <span className="wb-config-modal__help">
                Délai avant purge automatique des dossiers de sortie par le nettoyeur.
              </span>
            </div>

            {/* 3. Buffer de logs WebSocket */}
            <div className="wb-config-modal__section">
              <div className="wb-config-modal__field-header">
                <label htmlFor="modal_buffer" className="wb-config-modal__label">
                  <Terminal size={14} className="wb-config-modal__label-icon" />
                  <span>Capacité du tampon de logs (WebSocket) 📟</span>
                </label>
                <span className="wb-config-modal__pill">Replay</span>
              </div>

              <div className="wb-config-modal__input-row">
                <input
                  id="modal_buffer"
                  type="number"
                  min={100}
                  max={50000}
                  value={formData.buffer_max_lines ?? 5000}
                  disabled={loading || saving}
                  onChange={(e) => handleInputChange("buffer_max_lines", e.target.value)}
                  className="wb-input wb-config-modal__input"
                />
                <span className="wb-config-modal__unit">lignes 📜</span>
              </div>
              <span className="wb-config-modal__help">
                Lignes conservées en mémoire vive pour le replay en direct.
              </span>
            </div>

            {/* 4. Délai Déconnexion */}
            <div className="wb-config-modal__section">
              <div className="wb-config-modal__field-header">
                <label htmlFor="modal_delay" className="wb-config-modal__label">
                  <Clock size={14} className="wb-config-modal__label-icon" />
                  <span>Délai de grâce post-déconnexion 🔌</span>
                </label>
                <span className="wb-config-modal__preview">
                  ⏳ ~ {formatDuration(formData.buffer_clear_delay)}
                </span>
              </div>

              <div className="wb-config-modal__input-row">
                <input
                  id="modal_delay"
                  type="number"
                  min={10}
                  max={3600}
                  step={10}
                  value={formData.buffer_clear_delay}
                  disabled={loading || saving}
                  onChange={(e) => handleInputChange("buffer_clear_delay", e.target.value)}
                  className="wb-input wb-config-modal__input"
                />
                <span className="wb-config-modal__unit">secondes ⌛</span>
              </div>
              <span className="wb-config-modal__help">
                Délai accordé pour se reconnecter au socket avant vidange du buffer.
              </span>
            </div>
          </div>

          {/* ─── Pied de page d'actions ─── */}
          <div className="wb-config-modal__footer">
            <div className="wb-config-modal__footer-status">
              {isDirty ? (
                <span className="wb-badge wb-badge--warning">
                  <AlertCircle size={12} />
                  <span>Modifié ✍️</span>
                </span>
              ) : (
                <span className="wb-badge wb-badge--accent">
                  <Sparkles size={12} />
                  <span>À jour ✨</span>
                </span>
              )}
            </div>

            <div className="wb-config-modal__footer-buttons">
              <button
                type="button"
                onClick={handleReset}
                disabled={!isDirty || saving || loading}
                className="wb-btn wb-btn--ghost wb-config-modal__btn"
              >
                <RotateCcw size={14} />
                <span>Rétablir</span>
              </button>

              <button
                type="submit"
                disabled={!isDirty || saving || loading}
                className="wb-btn wb-btn--primary wb-config-modal__btn"
              >
                <Save size={14} />
                <span>{saving ? "Sauvegarde... ⏳" : "Sauvegarder 💾"}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ConfigModal;