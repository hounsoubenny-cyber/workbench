import React, { useState, useEffect, useRef, useMemo } from "react";
import { CreateJobResponse, JobOutputFile } from "@/types/types";
import { useJobLogs } from "@/hooks/use_job_logs";
import { downloadBackendFile, stopBackendJob } from "@/hooks/fetch_functions";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  Terminal,
  Download,
  Square,
  X,
  ChevronDown,
  ChevronUp,
  Eye,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Check,
  Search,
  Timer,
  Folder,
  Hash,
  Maximize2,
  Minimize2,
  FileDown,
  ArrowDownToLine,
  CheckCheck,
} from "lucide-react";

interface JobCardProps {
  job: CreateJobResponse;
  onRemove: (jobId: string) => void;
  onPreviewMedia: (workdir: string, filePath: string) => void;
}

type StreamTab = "all" | "stdout" | "stderr";

const formatTimer = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

// Helper pour afficher le badge de format approprié
const getFileTypeInfo = (filename: string | null) => {
  if (!filename) return { label: "FICHIER", icon: "📄", typeClass: "text" };
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (["mp4", "webm", "mkv", "mov", "avi"].includes(ext)) {
    return { label: ext.toUpperCase(), icon: "🎬", typeClass: "video" };
  }
  if (["gif", "png", "jpg", "jpeg", "webp", "ico", "avif", "bmp"].includes(ext)) {
    return { label: ext.toUpperCase(), icon: "🖼️", typeClass: "image" };
  }
  if (["mp3", "wav", "flac", "ogg", "aac", "m4a"].includes(ext)) {
    return { label: ext.toUpperCase(), icon: "🎧", typeClass: "audio" };
  }
  return { label: ext ? ext.toUpperCase() : "TXT", icon: "📄", typeClass: "text" };
};

// Analyseur et colorateur syntaxique CLI Pro
const formatLogLine = (text: string) => {
  if (/\b(error|failed|invalid|cannot|fatal|could not)\b/i.test(text)) {
    return (
      <span className="cli-log--error">
        <span className="cli-badge-err">ERR</span> {text}
      </span>
    );
  }
  if (/\b(warning|deprecated|not divisible|dropping|overwriting)\b/i.test(text)) {
    return (
      <span className="cli-log--warning">
        <span className="cli-badge-warn">WARN</span> {text}
      </span>
    );
  }
  if (text.includes("frame=") || text.includes("time=") || text.includes("bitrate=")) {
    const parts = text.split(/(\b(?:frame|fps|q|size|time|bitrate|speed)=[\w.:/-]+)/g);
    return (
      <span className="cli-log--progress">
        {parts.map((part, i) => {
          if (part.startsWith("time=") || part.startsWith("bitrate=")) {
            return <span key={i} className="cli-chip cli-chip--cyan">{part}</span>;
          }
          if (part.startsWith("frame=") || part.startsWith("fps=")) {
            return <span key={i} className="cli-chip cli-chip--green">{part}</span>;
          }
          if (part.startsWith("speed=") || part.startsWith("size=")) {
            return <span key={i} className="cli-chip cli-chip--accent">{part}</span>;
          }
          return <span key={i} className="cli-progress-dim">{part}</span>;
        })}
      </span>
    );
  }
  if (/^(Input #|Output #|Stream #|Stream mapping|Duration:|Metadata:)/.test(text.trim())) {
    return <span className="cli-log--stream-header">{text}</span>;
  }
  if (/^(configuration:|built with|ffmpeg version|libavutil|libavcodec|libavformat|libswscale|libpostproc)/i.test(text.trim())) {
    return <span className="cli-log--banner">{text}</span>;
  }
  if (text.trim().startsWith("[")) {
    const match = text.match(/^(\[[^\]]+\])(.*)$/);
    if (match) {
      return (
        <span className="cli-log--tagged">
          <span className="cli-tag">{match[1]}</span>
          <span className="cli-text">{match[2]}</span>
        </span>
      );
    }
  }
  return <span>{text}</span>;
};

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onRemove,
  onPreviewMedia,
}) => {
  const toast = useToast();

  const [isTerminalOpen, setIsTerminalOpen] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<StreamTab>("all");
  const [searchLog, setSearchLog] = useState("");
  const [copiedLogs, setCopiedLogs] = useState(false);
  const [copiedWorkdir, setCopiedWorkdir] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [outputFiles, setOutputFiles] = useState<JobOutputFile[]>(job.output_files || []);
  const [isStopping, setIsStopping] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const hasNotifiedRef = useRef(false);

  const { logs, status, jobResult } = useJobLogs(job.job_id, {
    onResult: (result) => {
      if (result && typeof result === "object" && !("returncode" in result)) {
        setOutputFiles((prev) =>
          prev.map((f) => {
            const resolved = result[f.id];
            return resolved ? { ...f, file: resolved } : f;
          })
        );
      }
    },
    onEnd: () => {
      if (!hasNotifiedRef.current) {
        hasNotifiedRef.current = true;
        toast.success("Job terminé !", {
          emoji: "🏁",
          description: `Le job ${job.job_id.slice(0, 14)}... est prêt.`,
        });
      }
    },
  });

  const isRunning = status === "connecting" || status === "connected";
  const isFinished = status === "finished";
  const isError = status === "error";

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setAutoScroll(true);
    }
  };

  useEffect(() => {
    let interval: any = null;
    if (isRunning) {
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning]);

  const returnCode: number | null = useMemo(() => {
    if (jobResult && typeof jobResult === "object" && "returncode" in jobResult) {
      return jobResult.returncode;
    }
    if (isFinished) return 0;
    return null;
  }, [jobResult, isFinished]);

  const stdoutLogs = useMemo(() => logs.filter((l) => l.stream === "stdout"), [logs]);
  const stderrLogs = useMemo(() => logs.filter((l) => l.stream === "stderr"), [logs]);

  const displayedLogs = useMemo(() => {
    let list = logs;
    if (activeTab === "stdout") list = stdoutLogs;
    if (activeTab === "stderr") list = stderrLogs;

    if (searchLog.trim()) {
      const q = searchLog.toLowerCase();
      list = list.filter((l) => l.text.toLowerCase().includes(q) || (l.step && l.step.toLowerCase().includes(q)));
    }
    return list;
  }, [logs, stdoutLogs, stderrLogs, activeTab, searchLog]);

  const handleCopyLogs = () => {
    if (displayedLogs.length === 0) return;
    const textToCopy = displayedLogs
      .map((l) => `${l.step ? `[${l.step}] ` : ""}${l.text}`)
      .join("\n");

    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopiedLogs(true);
      toast.success("Logs copiés !", { emoji: "📋" });
      setTimeout(() => setCopiedLogs(false), 2000);
    });
  };

  const handleDownloadLogFile = () => {
    if (logs.length === 0) return;
    const text = logs.map((l) => `[${l.stream.toUpperCase()}] ${l.step ? `[${l.step}] ` : ""}${l.text}`).join("\n");
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${job.job_id}.log`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Fichier .log téléchargé !", { emoji: "📄" });
  };

  const handleCopyWorkdir = () => {
    navigator.clipboard.writeText(job.workdir).then(() => {
      setCopiedWorkdir(true);
      toast.success("Chemin copié !", { emoji: "📁" });
      setTimeout(() => setCopiedWorkdir(false), 2000);
    });
  };

  const handleStop = async () => {
    setIsStopping(true);
    const res = await stopBackendJob(job.job_id);
    if (res.ok) toast.info("Demande d'arrêt envoyée", { emoji: "⏹️" });
    setIsStopping(false);
  };

  const handleClose = async () => {
    if (isRunning) {
      const confirmStop = window.confirm(
        "Ce job est encore en cours d'exécution. Voulez-vous l'arrêter et fermer son affichage ?"
      );
      if (!confirmStop) return;
      await stopBackendJob(job.job_id);
    }
    onRemove(job.job_id);
  };

  const handleDownloadAll = () => {
    const files = outputFiles.map((f) => f.file).filter(Boolean) as string[];
    if (files.length === 0) {
      toast.warning("Aucun fichier prêt pour l'instant", { emoji: "⏳" });
      return;
    }
    files.forEach((file) => downloadBackendFile(job.workdir, file));
    toast.success(`Téléchargement de ${files.length} fichier(s) lancé !`, { emoji: "📥" });
  };

  return (
    <div
      className={`wb-card wb-job-card ${isError ? "is-error" : isFinished ? "is-finished" : "is-running"} ${
        isFullscreen ? "is-fullscreen" : ""
      }`}
    >
      {/* ─── 1. En-tête de la Carte ─── */}
      <div className="wb-job-card__header">
        <div className="wb-job-card__title-meta">
          <div className="wb-job-card__main-title-row">
            {isRunning && <Loader2 size={16} className="wb-spin text-warning" />}
            {isFinished && <CheckCircle2 size={16} className="text-success" />}
            {isError && <AlertCircle size={16} className="text-danger" />}
            <span className="wb-job-card__spec-name">{job.spec.label || job.spec.id}</span>
          </div>

          <div className="wb-job-card__meta-pills-row">
            {returnCode !== null && (
              <span
                className={`wb-returncode-badge ${
                  returnCode === 0 ? "is-success" : returnCode === 1 ? "is-warn" : "is-fail"
                }`}
                title={`Code de retour : ${returnCode}`}
              >
                Code {returnCode} {returnCode === 0 ? "✓" : "✗"}
              </span>
            )}

            <span className="wb-job-card__pill">
              <Timer size={12} />
              <span>{formatTimer(elapsedSeconds)}</span>
            </span>

            <span className="wb-job-card__pill wb-job-card__pill--id" title={job.job_id}>
              <Hash size={11} />
              <span>{job.job_id.slice(0, 18)}...</span>
            </span>
          </div>

          <div className="wb-job-card__workdir-row">
            <span className="workdir-label">
              <Folder size={12} />
              <span>Workdir :</span>
            </span>
            <span className="workdir-path" title={job.workdir}>
              {job.workdir}
            </span>
            <button
              type="button"
              onClick={handleCopyWorkdir}
              className="workdir-copy-btn"
              title="Copier le chemin absolu"
            >
              {copiedWorkdir ? <Check size={11} className="text-success" /> : <Copy size={11} />}
            </button>
          </div>
        </div>

        <div className="wb-job-card__header-actions">
          <button
            type="button"
            className="wb-btn wb-btn--ghost wb-job-card__icon-btn"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? "Quitter le plein écran" : "Plein écran du terminal"}
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>

          <button
            type="button"
            className="wb-btn wb-btn--ghost wb-job-card__icon-btn"
            onClick={() => setIsTerminalOpen(!isTerminalOpen)}
            title={isTerminalOpen ? "Réduire le terminal" : "Afficher le terminal"}
          >
            <Terminal size={14} />
            {isTerminalOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {isRunning && (
            <button
              type="button"
              disabled={isStopping}
              onClick={handleStop}
              className="wb-btn wb-btn--ghost wb-job-card__stop-btn"
              title="Arrêter le processus CLI"
            >
              <Square size={12} fill="currentColor" />
              <span>Arrêter</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleClose}
            className="wb-job-card__close-btn"
            title="Fermer cette carte"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* ─── 2. Fichiers de Sorties & Téléchargements Sublimés ─── */}
      <div className="wb-job-card__files-bar">
        <div className="files-title-group">
          <span className="files-title">Sorties :</span>
        </div>

        <div className="files-chips">
          {outputFiles.length === 0 ? (
            <span className="file-none">Fichier de sortie en cours de génération...</span>
          ) : (
            outputFiles.map((f, idx) => {
              const fileInfo = getFileTypeInfo(f.file);
              return (
                <div key={idx} className="output-card">
                  {/* Badge de format coloré */}
                  <span className={`output-type-badge output-type-badge--${fileInfo.typeClass}`}>
                    <span className="type-icon">{fileInfo.icon}</span>
                    <span>{fileInfo.label}</span>
                  </span>

                  {/* Nom du fichier */}
                  <span className="output-name" title={f.file || undefined}>
                    {f.file || "Génération..."}
                  </span>

                  {/* Boutons d'action bien séparés et spacieux */}
                  {f.file && (
                    <div className="output-actions">
                      <button
                        type="button"
                        onClick={() => onPreviewMedia(job.workdir, f.file!)}
                        className="output-btn output-btn--view"
                        title="Prévisualiser dans le lecteur intégré"
                      >
                        <Eye size={13} />
                        <span>Voir</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => downloadBackendFile(job.workdir, f.file!)}
                        className="output-btn output-btn--dl"
                        title="Télécharger ce fichier"
                      >
                        <Download size={13} />
                        <span>Télécharger</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {outputFiles.some((f) => f.file) && (
          <button
            type="button"
            onClick={handleDownloadAll}
            className="wb-btn wb-btn--ghost dl-all-btn"
            title="Tout télécharger pour ce job"
          >
            <Download size={13} />
            <span>Tout télécharger ({outputFiles.filter((f) => f.file).length}) 📦</span>
          </button>
        )}
      </div>

      {/* ─── 3. Terminal Studio Haute Définition ─── */}
      <div
        className="wb-job-card__terminal-box"
        style={{ display: isTerminalOpen ? "flex" : "none" }}
      >
        <div className="wb-terminal-tabs-bar">
          <div className="wb-terminal-tabs">
            <button
              type="button"
              className={`wb-terminal-tab ${activeTab === "all" ? "active" : ""}`}
              onClick={() => setActiveTab("all")}
            >
              <span>Tous les flux</span>
              <span className="tab-count">{logs.length}</span>
            </button>

            <button
              type="button"
              className={`wb-terminal-tab ${activeTab === "stdout" ? "active" : ""}`}
              onClick={() => setActiveTab("stdout")}
            >
              <span>STDOUT 📤</span>
              <span className="tab-count">{stdoutLogs.length}</span>
            </button>

            <button
              type="button"
              className={`wb-terminal-tab ${activeTab === "stderr" ? "active" : ""}`}
              onClick={() => setActiveTab("stderr")}
            >
              <span>STDERR 📥</span>
              <span className={`tab-count ${stderrLogs.length > 0 && isError ? "has-stderr" : ""}`}>
                {stderrLogs.length}
              </span>
            </button>
          </div>

          <div className="wb-terminal-right-tools">
            <div className="terminal-search-box">
              <Search size={12} className="search-icon" />
              <input
                type="text"
                placeholder="Filtrer..."
                value={searchLog}
                onChange={(e) => setSearchLog(e.target.value)}
                className="terminal-search-input"
              />
              {searchLog && (
                <button type="button" onClick={() => setSearchLog("")} className="search-clear">
                  <X size={10} />
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={handleDownloadLogFile}
              disabled={logs.length === 0}
              className="wb-btn wb-btn--ghost terminal-copy-btn"
              title="Exporter les logs en fichier .log"
            >
              <FileDown size={12} />
              <span>.log</span>
            </button>

            <button
              type="button"
              onClick={handleCopyLogs}
              disabled={displayedLogs.length === 0}
              className="wb-btn wb-btn--ghost terminal-copy-btn"
              title="Copier les logs affichés"
            >
              {copiedLogs ? <Check size={12} className="text-success" /> : <Copy size={12} />}
              <span>{copiedLogs ? "Copié !" : "Copier"}</span>
            </button>
          </div>
        </div>

        <div className="terminal-logs-wrapper">
          <div
            className="terminal-logs"
            ref={scrollRef}
            onScroll={handleScroll}
          >
            {displayedLogs.length === 0 ? (
              isFinished ? (
                <div className="terminal-silent-success">
                  <CheckCheck size={28} className="text-success" />
                  <div className="silent-text">
                    <h5>Exécution terminée avec succès (Code 0) ✨</h5>
                    <p>
                      {outputFiles.some((f) => f.file)
                        ? "Vos fichiers de sortie ont été générés sans erreur."
                        : "Le processus s'est terminé sans émettre de message de log."}
                    </p>
                  </div>
                </div>
              ) : isError ? (
                <div className="terminal-waiting text-danger">
                  Le processus s'est arrêté avec une erreur sans émettre de log.
                </div>
              ) : (
                <div className="terminal-waiting">En attente des logs CLI...</div>
              )
            ) : (
              displayedLogs.map((l, idx) => (
                <div key={l.id} className={`terminal-line line-${l.stream}`}>
                  <span className="terminal-line-num">{idx + 1}</span>
                  {l.step && <span className="line-step">[{l.step}]</span>}
                  <span className="line-text">{formatLogLine(l.text)}</span>
                </div>
              ))
            )}
          </div>

          {!autoScroll && logs.length > 10 && (
            <button
              type="button"
              onClick={scrollToBottom}
              className="wb-terminal-autoscroll-btn"
              title="Descendre vers les logs les plus récents"
            >
              <ArrowDownToLine size={13} />
              <span>Suivre le direct ⬇️</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};