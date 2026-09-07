import React, { useState, useEffect } from "react";
import "./job_create_modal.css";
import { SpecSummary, ModelSchema, CreateJobResponse } from "@/types/types";
import { getBackendSpecInfo } from "@/hooks/fetch_functions";
import { launchCatalogJob } from "@/hooks/utils";
import { DynamicInput } from "@/components/utils/dynamic_input/dynamique_input";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  X,
  Play,
  Sparkles,
  Clock,
  Layers,
  AlertCircle,
  RotateCcw,
} from "lucide-react";

interface JobCreateModalProps {
  isOpen: boolean;
  spec: SpecSummary | null;
  onClose: () => void;
  onJobCreated: (job: CreateJobResponse) => void;
}

export const JobCreateModal: React.FC<JobCreateModalProps> = ({
  isOpen,
  spec,
  onClose,
  onJobCreated,
}) => {
  const toast = useToast();
  const [schema, setSchema] = useState<ModelSchema | null>(null);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, File | File[]>>({});
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(300);
  const [loadingSchema, setLoadingSchema] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Chargement du schéma d'introspection Pydantic
  useEffect(() => {
    if (!isOpen || !spec) {
      setSchema(null);
      setFormValues({});
      setUploadedFiles({});
      return;
    }

    setLoadingSchema(true);
    getBackendSpecInfo(spec.id).then((res) => {
      if (res.ok && res.response) {
        setSchema(res.response.input);
        // Initialisation des valeurs par défaut
        const initialVals: Record<string, any> = {};
        Object.entries(res.response.input).forEach(([key, meta]) => {
          if (meta?.default !== null && meta?.default !== undefined) {
            initialVals[key] = meta.default;
          }
        });
        setFormValues(initialVals);
      } else {
        toast.error("Échec de chargement des paramètres", {
          emoji: "⚠️",
          description: res.error || "Impossible d'introspecter cette spec.",
        });
      }
      setLoadingSchema(false);
    });
  }, [isOpen, spec]);

  const handleFieldChange = (key: string, value: any, file?: File | File[]) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    if (file) {
      setUploadedFiles((prev) => ({ ...prev, [key]: file }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!spec || submitting) return;

    // Aplatit tous les fichiers dans un seul tableau ordonné
    const filesToUpload: File[] = [];
    Object.values(uploadedFiles).forEach((f) => {
      if (Array.isArray(f)) {
        filesToUpload.push(...f);
      } else if (f) {
        filesToUpload.push(f);
      }
    });

    let launchError: string | null = null;

    const result = await launchCatalogJob(
      spec.id,
      formValues,
      filesToUpload,
      timeoutSeconds,
      null,
      (err) => {
        launchError = err;
      },
      setSubmitting
    );

    if (result) {
      toast.success("Job démarré avec succès !", {
        emoji: "🚀",
        description: `Identifiant : ${result.job_id.slice(0, 16)}...`,
      });
      onJobCreated(result);
      onClose();
    } else {
      toast.error("Échec de création du job", {
        emoji: "💥",
        description: launchError || "Vérifiez vos paramètres ou les fichiers sélectionnés.",
      });
    }
  };

  if (!isOpen || !spec) return null;

  return (
    <div
      className="wb-job-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="wb-job-modal">
        {/* ─── Header ─── */}
        <div className="wb-job-modal__header">
          <div className="wb-job-modal__title-group">
            <span className="wb-badge wb-badge--accent">
              <Layers size={13} /> {spec.type === "pipeline" ? "Super-Pipeline" : "Action CLI"}
            </span>
            <h3 className="wb-job-modal__title">{spec.label || spec.id}</h3>
          </div>

          <button
            type="button"
            disabled={submitting}
            onClick={onClose}
            className="wb-job-modal__close-btn"
          >
            <X size={18} />
          </button>
        </div>

        {/* ─── Corps avec formulaire dynamique ─── */}
        <form onSubmit={handleSubmit} className="wb-job-modal__form">
          <div className="wb-job-modal__body">
            {loadingSchema ? (
              <div className="wb-job-modal__loading">
                <span className="wb-spin">⚙️</span>
                <span>Génération du formulaire dynamique en cours...</span>
              </div>
            ) : schema && Object.keys(schema).length > 0 ? (
              <div className="wb-job-modal__fields-list">
                {Object.entries(schema).map(([fieldKey, fieldMeta]) => (
                  <DynamicInput
                    key={fieldKey}
                    fieldKey={fieldKey}
                    data={fieldMeta}
                    value={formValues[fieldKey]}
                    onSave={handleFieldChange}
                    disabled={submitting}
                  />
                ))}
              </div>
            ) : (
              <div className="wb-job-modal__empty-fields">
                <Sparkles size={20} className="empty-icon" />
                <p>Cette action ne requiert aucun paramètre d'entrée spécifique.</p>
              </div>
            )}

            {/* Timeout global */}
            <div className="wb-job-modal__timeout-row">
              <label htmlFor="job_timeout" className="wb-job-modal__timeout-label">
                <Clock size={14} />
                <span>Temps limite d'exécution (Timeout) :</span>
              </label>
              <div className="wb-job-modal__timeout-input-group">
                <input
                  id="job_timeout"
                  type="number"
                  min={10}
                  max={3600}
                  step={10}
                  value={timeoutSeconds}
                  disabled={submitting}
                  onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                  className="wb-input wb-job-modal__timeout-input"
                />
                <span>secondes ⏱️</span>
              </div>
            </div>
          </div>

          {/* ─── Footer d'actions ─── */}
          <div className="wb-job-modal__footer">
            <button
              type="button"
              disabled={submitting}
              onClick={onClose}
              className="wb-btn wb-btn--ghost"
            >
              Annuler
            </button>

            <button
              type="submit"
              disabled={submitting || loadingSchema}
              className="wb-btn wb-btn--primary wb-job-modal__submit-btn"
            >
              <Play size={14} fill="currentColor" />
              <span>{submitting ? "Initialisation..." : "Lancer le Traitement 🚀"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};