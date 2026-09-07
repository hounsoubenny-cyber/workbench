import React, { useState, useEffect } from "react";
import "./config_page.css";
import { WbConfig } from "@/types/types";
import { fetchServerConfig, updateServerConfig } from "@/hooks/utils";
import { useToast } from "@/components/utils/toast/toast_context";
import {
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
  Trash2,
  ScrollText,
  Timer,
  AlertCircle,
} from "lucide-react";

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

export const ConfigPage: React.FC = () => {
  const toast = useToast();

  // Config originale en provenance du backend
  const [initialConfig, setInitialConfig] = useState<WbConfig | null>(null);

  // État local éditable
  const [formData, setFormData] = useState<WbConfig>({
    max_concurrent_job: 10,
    buffer_max_lines: 5000,
    buffer_clear_delay: 120,
    file_ttl: 3600,
  });

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  // Chargement de la config avec feedback toast
  const loadConfig = async (isManualRefresh: boolean = false) => {
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

    if (fetchError) {
      toast.error("Impossible de joindre le serveur", {
        emoji: "📡",
        description: fetchError,
      });
    } else if (conf && isManualRefresh) {
      toast.success("Configuration synchronisée !", {
        emoji: "🔄",
        description: "Les paramètres du moteur ont été rechargés.",
      });
    }
  };

  useEffect(() => {
    loadConfig(false);
  }, []);

  // Détection si l'utilisateur a apporté des modifications
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
        description: "Les valeurs ont été remises à l'état initial du serveur.",
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
      toast.success("Paramètres enregistrés avec succès !", {
        emoji: "✨",
        description: "Appliqués en direct aux moteurs FFmpeg, SoX et ImageMagick.",
      });
    } else {
      toast.error("Échec de l'enregistrement", {
        emoji: "💥",
        description: saveError || "Une erreur est survenue lors de l'écriture du fichier de config.",
      });
    }
  };

  return (
    <div className="wb-config-container">
      {/* ─── En-tête de page ─── */}
      <div className="wb-config-header">
        <div className="wb-config-header__titles">
          <div className="wb-config-header__tag">
            <span className="wb-config-header__tag-emoji">⚙️</span>
            <Sliders size={13} />
            <span>Moteur Système</span>
          </div>

          <h1 className="wb-config-header__title">
            Configuration Moteur <span className="wb-config-header__emoji-title">🎛️</span>
          </h1>

          <p className="wb-config-header__subtitle">
            Pilotez les quotas de calcul simultanés, la durée de rétention des fichiers temporaires
            et la taille des tampons WebSocket de streaming.
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadConfig(true)}
          disabled={loading || saving}
          className="wb-btn wb-btn--ghost wb-config-header__refresh"
          title="Recharger depuis le serveur"
        >
          <RefreshCw size={15} className={loading ? "wb-spin" : ""} />
          <span>Rafraîchir 🔄</span>
        </button>
      </div>

      {/* ─── Formulaire de configuration ─── */}
      <form onSubmit={handleSubmit} className="wb-config-form">
        <div className="wb-config-grid">
          {/* CARTE 1 : Parallélisme & Concurrence */}
          <div className="wb-card wb-config-card">
            <div className="wb-config-card__header">
              <span className="wb-config-card__icon-badge">
                <span className="wb-config-card__badge-emoji">⚡</span>
                <Cpu size={16} />
              </span>
              <div>
                <h3 className="wb-config-card__title">Concurrence d'exécution</h3>
                <span className="wb-config-card__desc">Allocation CPU & Processus CLI</span>
              </div>
            </div>

            <div className="wb-config-card__body">
              <div className="wb-config-field">
                <div className="wb-config-field__top">
                  <label htmlFor="max_concurrent_job" className="wb-config-field__label">
                    Tâches simultanées max
                  </label>
                  <span className="wb-config-field__badge">
                    <Zap size={11} /> 1 à 64 jobs
                  </span>
                </div>

                <div className="wb-config-field__input-row">
                  <input
                    id="max_concurrent_job"
                    type="number"
                    min={1}
                    max={64}
                    value={formData.max_concurrent_job}
                    disabled={loading || saving}
                    onChange={(e) => handleInputChange("max_concurrent_job", e.target.value)}
                    className="wb-input wb-config-input"
                  />
                  <span className="wb-config-field__unit">processus 🚀</span>
                </div>

                <p className="wb-config-field__hint">
                  Nombre maximal de commandes exécutées en parallèle. Les requêtes suivantes recevront un code <code>429 Too Many Jobs</code> pour protéger le système contre la saturation mémoire.
                </p>
              </div>
            </div>
          </div>

          {/* CARTE 2 : Rétention Fichiers (TTL) */}
          <div className="wb-card wb-config-card">
            <div className="wb-config-card__header">
              <span className="wb-config-card__icon-badge">
                <span className="wb-config-card__badge-emoji">🧹</span>
                <HardDrive size={16} />
              </span>
              <div>
                <h3 className="wb-config-card__title">Rétention des fichiers (TTL)</h3>
                <span className="wb-config-card__desc">Purge automatique du disque de travail</span>
              </div>
            </div>

            <div className="wb-config-card__body">
              <div className="wb-config-field">
                <div className="wb-config-field__top">
                  <label htmlFor="file_ttl" className="wb-config-field__label">
                    Durée de vie avant suppression
                  </label>
                  <span className="wb-config-field__preview">
                    ⏳ ~ {formatDuration(formData.file_ttl)}
                  </span>
                </div>

                <div className="wb-config-field__input-row">
                  <input
                    id="file_ttl"
                    type="number"
                    min={60}
                    step={60}
                    value={formData.file_ttl}
                    disabled={loading || saving}
                    onChange={(e) => handleInputChange("file_ttl", e.target.value)}
                    className="wb-input wb-config-input"
                  />
                  <span className="wb-config-field__unit">secondes ⏱️</span>
                </div>

                <p className="wb-config-field__hint">
                  Délai avant suppression automatique des dossiers temporaires et médias par <code>AsyncJobFileCleaner</code>. Un fichier téléchargé reste disponible pendant cette durée.
                </p>
              </div>
            </div>
          </div>

          {/* CARTE 3 : Flux Live & WebSocket */}
          <div className="wb-card wb-config-card">
            <div className="wb-config-card__header">
              <span className="wb-config-card__icon-badge">
                <span className="wb-config-card__badge-emoji">📟</span>
                <Terminal size={16} />
              </span>
              <div>
                <h3 className="wb-config-card__title">Tampon WebSocket (Logs)</h3>
                <span className="wb-config-card__desc">Capacité de relecture du flux live</span>
              </div>
            </div>

            <div className="wb-config-card__body">
              <div className="wb-config-field">
                <div className="wb-config-field__top">
                  <label htmlFor="buffer_max_lines" className="wb-config-field__label">
                    Lignes en mémoire par job
                  </label>
                  <span className="wb-config-field__badge">
                    <ScrollText size={11} /> Replay
                  </span>
                </div>

                <div className="wb-config-field__input-row">
                  <input
                    id="buffer_max_lines"
                    type="number"
                    min={100}
                    max={50000}
                    value={formData.buffer_max_lines ?? 5000}
                    disabled={loading || saving}
                    onChange={(e) => handleInputChange("buffer_max_lines", e.target.value)}
                    className="wb-input wb-config-input"
                  />
                  <span className="wb-config-field__unit">lignes 📜</span>
                </div>

                <p className="wb-config-field__hint">
                  Nombre max de lignes <code>stdout/stderr</code> conservées en mémoire pour le rejeu (replay) lors de la reconnexion au socket d'un job en cours.
                </p>
              </div>
            </div>
          </div>

          {/* CARTE 4 : Nettoyage Déconnexion */}
          <div className="wb-card wb-config-card">
            <div className="wb-config-card__header">
              <span className="wb-config-card__icon-badge">
                <span className="wb-config-card__badge-emoji">🔌</span>
                <Clock size={16} />
              </span>
              <div>
                <h3 className="wb-config-card__title">Délai de grâce déconnexion</h3>
                <span className="wb-config-card__desc">Nettoyage mémoire post-fermeture</span>
              </div>
            </div>

            <div className="wb-config-card__body">
              <div className="wb-config-field">
                <div className="wb-config-field__top">
                  <label htmlFor="buffer_clear_delay" className="wb-config-field__label">
                    Délai avant purge du buffer
                  </label>
                  <span className="wb-config-field__preview">
                    ⏳ ~ {formatDuration(formData.buffer_clear_delay)}
                  </span>
                </div>

                <div className="wb-config-field__input-row">
                  <input
                    id="buffer_clear_delay"
                    type="number"
                    min={10}
                    max={3600}
                    step={10}
                    value={formData.buffer_clear_delay}
                    disabled={loading || saving}
                    onChange={(e) => handleInputChange("buffer_clear_delay", e.target.value)}
                    className="wb-input wb-config-input"
                  />
                  <span className="wb-config-field__unit">secondes ⌛</span>
                </div>

                <p className="wb-config-field__hint">
                  Temps accordé au navigateur pour se reconnecter à son flux WebSocket après un rafraîchissement ou une coupure réseau, avant vidange définitive de la mémoire.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Barre d'action inférieure ─── */}
        <div className="wb-config-footer">
          <div className="wb-config-footer__status">
            {isDirty ? (
              <span className="wb-badge wb-badge--warning wb-config-status-badge">
                <AlertCircle size={13} />
                <span>Modifications non enregistrées ✍️</span>
              </span>
            ) : (
              <span className="wb-badge wb-badge--accent wb-config-status-badge">
                <Sparkles size={13} />
                <span>Configuration synchronisée ✨</span>
              </span>
            )}
          </div>

          <div className="wb-config-footer__actions">
            <button
              type="button"
              onClick={handleReset}
              disabled={!isDirty || saving || loading}
              className="wb-btn wb-btn--ghost"
            >
              <RotateCcw size={15} />
              <span>Rétablir ↩️</span>
            </button>

            <button
              type="submit"
              disabled={!isDirty || saving || loading}
              className="wb-btn wb-btn--primary wb-config-save-btn"
            >
              <Save size={15} />
              <span>{saving ? "Enregistrement en cours... ⏳" : "Enregistrer 💾"}</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default ConfigPage;