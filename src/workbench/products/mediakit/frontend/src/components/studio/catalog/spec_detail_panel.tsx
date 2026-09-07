import React, { useEffect, useState } from "react";
import "./spec_detail_panel.css";
import { SpecSummary, ActionSummary, PipelineSummary, SpecInfoResponse } from "@/types/types";
import { getBackendSpecInfo } from "@/hooks/fetch_functions";
import {
  X,
  Play,
  Workflow,
  Film,
  Music,
  Image as ImageIcon,
  CheckCircle2,
  Code2,
  Layers,
  ArrowDown,
} from "lucide-react";

interface SpecDetailPanelProps {
  spec: SpecSummary | null;
  onClose: () => void;
  onLaunch: (spec: SpecSummary) => void;
  disabled?: boolean;
}

export const SpecDetailPanel: React.FC<SpecDetailPanelProps> = ({
  spec,
  onClose,
  onLaunch,
  disabled = false,
}) => {
  const [info, setInfo] = useState<SpecInfoResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!spec) {
      setInfo(null);
      return;
    }
    let isMounted = true;
    setLoading(true);

    getBackendSpecInfo(spec.id).then((res) => {
      if (isMounted && res.ok && res.response) {
        setInfo(res.response as SpecInfoResponse);
      }
      if (isMounted) setLoading(false);
    });

    return () => {
      isMounted = false;
    };
  }, [spec]);

  if (!spec) return null;

  const isPipeline = spec.type === "pipeline";
  const pipelineSteps = isPipeline ? (spec as PipelineSummary).steps || [] : [];

  return (
    <div className="wb-spec-detail-panel">
      {/* ─── En-tête ─── */}
      <div className="wb-spec-detail__header">
        <div className="wb-spec-detail__badge-group">
          <span className={`wb-badge ${isPipeline ? "wb-badge--accent" : "wb-badge--info"}`}>
            {isPipeline ? "Super-Pipeline" : (spec as ActionSummary).tool}
          </span>
          <span className="wb-spec-detail__id">{spec.id}</span>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="wb-spec-detail__close-btn"
          title="Désélectionner et fermer le détail"
        >
          <X size={18} />
        </button>
      </div>

      <div className="wb-spec-detail__body">
        <h3 className="wb-spec-detail__title">{spec.label || spec.id}</h3>

        {/* ─── Fil d'étapes si Pipeline ─── */}
        {isPipeline && (
          <div className="wb-spec-detail__pipeline-steps">
            <span className="wb-spec-detail__steps-title">
              <Workflow size={14} /> Étapes du workflow chaîné :
            </span>
            <div className="wb-spec-detail__timeline">
              {pipelineSteps.map((step, idx) => (
                <React.Fragment key={step.id}>
                  <div className="wb-spec-detail__step-node">
                    <span className="step-num">{idx + 1}</span>
                    <div className="step-info">
                      <div className="step-title-row">
                        <span className="step-label">{step.label || step.action_id}</span>
                        <span className="step-tool-badge">{step.tool.toUpperCase()}</span>
                      </div>
                      <span className="step-id-slug">id: {step.id} ({step.action_id})</span>
                    </div>
                  </div>
                  {idx < pipelineSteps.length - 1 && (
                    <ArrowDown size={14} className="step-arrow" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* ─── Schéma des Paramètres Requis ─── */}
        <div className="wb-spec-detail__params-section">
          <span className="wb-spec-detail__params-title">
            <Code2 size={14} /> Paramètres requis (Introspection Pydantic) :
          </span>

          {loading ? (
            <div className="wb-spec-detail__loading">Chargement des entrées...</div>
          ) : info?.input ? (
            <div className="wb-spec-detail__params-list">
              {Object.entries(info.input).map(([fieldName, fieldMeta]) => (
                <div key={fieldName} className="wb-spec-detail__param-chip">
                  <span className="param-name">{fieldMeta.name}</span>
                  <span className="param-type">{fieldMeta.type}</span>
                  {fieldMeta.is_upload && <span className="param-upload">Upload requis 📁</span>}
                </div>
              ))}
            </div>
          ) : (
            <div className="wb-spec-detail__no-params">Aucun paramètre additionnel requis.</div>
          )}
        </div>
      </div>

      {/* ─── Pied d'action ─── */}
      <div className="wb-spec-detail__footer">
        <button
          type="button"
          onClick={onClose}
          className="wb-btn wb-btn--ghost"
        >
          Désélectionner ✕
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => onLaunch(spec)}
          className="wb-btn wb-btn--primary"
        >
          <Play size={14} fill="currentColor" />
          <span>Lancer l'action 🚀</span>
        </button>
      </div>
    </div>
  );
};