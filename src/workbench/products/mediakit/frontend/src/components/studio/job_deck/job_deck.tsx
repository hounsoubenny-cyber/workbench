import React, { useState } from "react";
import "./job_deck.css";
import { CreateJobResponse } from "@/types/types";
import { JobCard } from "./job_card";
import { downloadBackendFile, stopBackendJob } from "@/hooks/fetch_functions";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  Terminal,
  Download,
  ChevronDown,
  ChevronUp,
  Trash2,
} from "lucide-react";

interface JobDeckProps {
  jobs: CreateJobResponse[];
  onRemoveJob: (jobId: string) => void;
  onClearAllJobs: () => void;
  onPreviewMedia: (workdir: string, filePath: string) => void;
}

export const JobDeck: React.FC<JobDeckProps> = ({
  jobs,
  onRemoveJob,
  onClearAllJobs,
  onPreviewMedia,
}) => {
  const toast = useToast();
  const [isMinimized, setIsMinimized] = useState(false);

  if (jobs.length === 0) return null;

  // Télécharger tous les fichiers de tous les jobs terminés
  const handleDownloadAllFinished = () => {
    let count = 0;
    jobs.forEach((job) => {
      job.output_files?.forEach((f) => {
        if (f.file) {
          downloadBackendFile(job.workdir, f.file);
          count++;
        }
      });
    });

    if (count > 0) {
      toast.success(`${count} fichier(s) en cours de téléchargement !`, { emoji: "📦" });
    } else {
      toast.info("Aucun fichier prêt pour le moment.", { emoji: "⏳" });
    }
  };

  // Fermer tous les jobs avec sécurité
  const handleClearAllWithSafety = async () => {
    const confirmClear = window.confirm(
      `Voulez-vous fermer l'ensemble des ${jobs.length} jobs affichés ? Tout job encore en cours d'exécution sera immédiatement stoppé.`
    );
    if (!confirmClear) return;

    // Arrête préventivement tous les jobs en arrière-plan
    await Promise.all(jobs.map((j) => stopBackendJob(j.job_id)));
    onClearAllJobs();
    toast.info("Tous les terminaux ont été fermés", { emoji: "🧹" });
  };

  return (
    <div className={`wb-job-deck ${isMinimized ? "is-minimized" : ""}`}>
      {/* ─── Barre Supérieure du Deck ─── */}
      <div className="wb-job-deck__bar">
        <div className="wb-job-deck__left">
          <span className="deck-badge">
            <Terminal size={14} />
            <span>Job Deck Live ({jobs.length})</span>
          </span>
          <span className="deck-hint">Multi-terminaux actifs en temps réel</span>
        </div>

        <div className="wb-job-deck__right">
          {/* Bouton Télécharger Tous les Finis */}
          <button
            type="button"
            onClick={handleDownloadAllFinished}
            className="wb-btn wb-btn--ghost deck-btn"
            title="Télécharger tous les fichiers produits par les jobs terminés"
          >
            <Download size={13} />
            <span>Télécharger tout (finis) 📦</span>
          </button>

          {/* Bouton Tout Fermer */}
          <button
            type="button"
            onClick={handleClearAllWithSafety}
            className="wb-btn wb-btn--ghost deck-btn deck-btn--danger"
            title="Arrêter et fermer tous les terminaux"
          >
            <Trash2 size={13} />
            <span>Tout fermer 🗑️</span>
          </button>

          {/* Réduire / Agrandir le Deck */}
          <button
            type="button"
            onClick={() => setIsMinimized(!isMinimized)}
            className="wb-btn wb-btn--ghost deck-btn"
            title={isMinimized ? "Agrandir le deck" : "Réduire le deck"}
          >
            {isMinimized ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            <span>{isMinimized ? "Agrandir" : "Réduire"}</span>
          </button>
        </div>
      </div>

      {/* ─── Grille des Jobs ─── */}
      <div
        className="wb-job-deck__content"
        style={{ display: isMinimized ? "none" : "block" }}
      >
        <div className="wb-job-deck__grid">
          {jobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              onRemove={onRemoveJob}
              onPreviewMedia={onPreviewMedia}
            />
          ))}
        </div>
      </div>
    </div>
  );
};