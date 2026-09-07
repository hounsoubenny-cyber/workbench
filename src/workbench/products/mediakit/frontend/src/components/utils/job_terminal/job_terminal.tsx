import React, { useEffect, useRef, useState } from "react";
import "./job_terminal.css";
import { useJobLogs } from "@/hooks/use_job_logs";

interface JobTerminalProps {
  jobId: string | null;
  title?: string;
  onJobFinished?: (result: any) => void;
  maxHeight?: string;
}

export const JobTerminal: React.FC<JobTerminalProps> = ({
  jobId,
  title = "Console d'exécution",
  onJobFinished,
  maxHeight = "360px",
}) => {
  const { logs, status, isReplaying, reconnect, clearLogs } = useJobLogs(jobId, {
    onResult: onJobFinished,
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Défilement automatique vers le bas à chaque nouvelle ligne
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Si l'utilisateur remonte manuellement la molette, on désactive l'autoscroll
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  const getStatusBadge = () => {
    switch (status) {
      case "connecting":
        return <span className="wb-badge wb-badge--warning">Connexion...</span>;
      case "connected":
        return <span className="wb-badge wb-badge--info">En direct</span>;
      case "finished":
        return <span className="wb-badge wb-badge--success">Terminé</span>;
      case "error":
        return <span className="wb-badge wb-badge--danger">Erreur flux</span>;
      default:
        return <span className="wb-badge">En attente</span>;
    }
  };

  return (
    <div className="wb-terminal-card">
      <div className="wb-terminal-header">
        <div className="wb-terminal-title-group">
          <span className="wb-terminal-indicator" data-status={status} />
          <h4 className="wb-terminal-title">{title}</h4>
          {getStatusBadge()}
          {isReplaying && (
            <span className="wb-badge wb-badge--accent">Replay historique</span>
          )}
        </div>

        <div className="wb-terminal-actions">
          <button
            type="button"
            className="wb-btn wb-btn--ghost wb-terminal-btn"
            onClick={clearLogs}
            title="Effacer l'affichage"
          >
            Effacer
          </button>
          {status === "error" && (
            <button
              type="button"
              className="wb-btn wb-btn--primary wb-terminal-btn"
              onClick={reconnect}
            >
              Reconnexion
            </button>
          )}
        </div>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        style={{ maxHeight }}
        className="wb-terminal-body"
      >
        {logs.length === 0 ? (
          <div className="wb-terminal-empty">
            {status === "connecting"
              ? "Ouverture du flux temps réel..."
              : "En attente des logs CLI..."}
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className={`wb-terminal-line wb-terminal-line--${log.stream}`}
            >
              {log.step && (
                <span className="wb-terminal-step">[{log.step}]</span>
              )}
              {log.timestamp && (
                <span className="wb-terminal-time">
                  {log.timestamp.slice(11, 19)}
                </span>
              )}
              <span className="wb-terminal-text">{log.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};