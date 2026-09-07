import React, { useEffect } from "react";
import { AlertTriangle, AlertOctagon, Info, X } from "lucide-react";
import "./confirm_modal.css";

export type ConfirmVariant = "danger" | "warning" | "info" | "primary";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText = "Confirmer",
  cancelText = "Annuler",
  variant = "danger",
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isLoading, onCancel]);

  if (!isOpen) return null;

  const getIcon = () => {
    switch (variant) {
      case "danger":
        return <AlertOctagon size={24} className="confirm-modal__icon confirm-modal__icon--danger" />;
      case "warning":
        return <AlertTriangle size={24} className="confirm-modal__icon confirm-modal__icon--warning" />;
      case "info":
      case "primary":
      default:
        return <Info size={24} className="confirm-modal__icon confirm-modal__icon--info" />;
    }
  };

  return (
    <div className="confirm-modal-overlay" onClick={isLoading ? undefined : onCancel}>
      <div className="confirm-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-modal__header">
          <div className="confirm-modal__title-group">
            {getIcon()}
            <h3 className="confirm-modal__title">{title}</h3>
          </div>
          {!isLoading && (
            <button type="button" className="confirm-modal__close-btn" onClick={onCancel}>
              <X size={16} />
            </button>
          )}
        </div>

        <div className="confirm-modal__body">
          <p className="confirm-modal__message">{message}</p>
        </div>

        <div className="confirm-modal__footer">
          <button
            type="button"
            className="oh-btn oh-btn--ghost confirm-modal__btn"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`oh-btn confirm-modal__btn confirm-modal__btn--${variant}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "Action en cours..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}