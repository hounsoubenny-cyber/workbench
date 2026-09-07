import React, { useEffect, useState } from "react";
import "./media_preview_modal.css";
import { getDownloadFileUrl, downloadBackendFile } from "@/hooks/fetch_functions";
import { X, Download, FileText, Film, Music, Image as ImageIcon } from "lucide-react";

interface MediaPreviewModalProps {
  workdir: string | null;
  filePath: string | null;
  onClose: () => void;
}

export const MediaPreviewModal: React.FC<MediaPreviewModalProps> = ({
  workdir,
  filePath,
  onClose,
}) => {
  const [mediaUrl, setMediaUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!workdir || !filePath) {
      setMediaUrl(null);
      return;
    }
    getDownloadFileUrl(workdir, filePath).then((url) => setMediaUrl(url));
  }, [workdir, filePath]);

  if (!workdir || !filePath || !mediaUrl) return null;

  const ext = filePath.split(".").pop()?.toLowerCase() || "";
  const filename = filePath.split("/").pop() || filePath;

  const isVideo = ["mp4", "webm", "mkv", "mov", "avi"].includes(ext);
  const isAudio = ["mp3", "wav", "flac", "ogg", "aac", "m4a"].includes(ext);
  const isImage = ["png", "jpg", "jpeg", "webp", "gif", "ico", "bmp", "avif"].includes(ext);

  return (
    <div
      className="wb-preview-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="wb-preview-modal">
        {/* En-tête */}
        <div className="wb-preview-header">
          <div className="wb-preview-title-group">
            {isVideo && <Film size={16} className="wb-preview-type-icon is-video" />}
            {isAudio && <Music size={16} className="wb-preview-type-icon is-audio" />}
            {isImage && <ImageIcon size={16} className="wb-preview-type-icon is-image" />}
            {!isVideo && !isAudio && !isImage && <FileText size={16} />}
            <span className="wb-preview-filename">{filename}</span>
          </div>

          <div className="wb-preview-actions">
            <button
              type="button"
              onClick={() => downloadBackendFile(workdir, filePath, filename)}
              className="wb-btn wb-btn--primary wb-preview-dl-btn"
            >
              <Download size={14} />
              <span>Télécharger</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="wb-preview-close"
              aria-label="Fermer la prévisualisation"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Corps média */}
        <div className="wb-preview-body">
          {isVideo && (
            <video controls autoPlay className="wb-preview-media wb-preview-media--video">
              <source src={mediaUrl} type={`video/${ext === "mp4" ? "mp4" : ext}`} />
              Votre navigateur ne supporte pas ce lecteur vidéo.
            </video>
          )}

          {isAudio && (
            <div className="wb-preview-audio-container">
              <span className="wb-preview-audio-emoji">🎵</span>
              <audio controls autoPlay className="wb-preview-media wb-preview-media--audio">
                <source src={mediaUrl} type={`audio/${ext === "mp3" ? "mpeg" : ext}`} />
                Votre navigateur ne supporte pas ce lecteur audio.
              </audio>
            </div>
          )}

          {isImage && (
            <img src={mediaUrl} alt={filename} className="wb-preview-media wb-preview-media--image" />
          )}

          {!isVideo && !isAudio && !isImage && (
            <div className="wb-preview-unknown">
              <FileText size={48} />
              <p>Aperçu non disponible directement pour le format <code>.{ext}</code>.</p>
              <button
                type="button"
                onClick={() => downloadBackendFile(workdir, filePath, filename)}
                className="wb-btn wb-btn--ghost"
              >
                Télécharger le fichier pour le consulter
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};