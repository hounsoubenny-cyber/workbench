import "./password_prompt.css";
import { useState, useRef, useEffect } from "react";
import { Lock, X, Eye, EyeOff, ShieldCheck } from "lucide-react";

interface PasswordPromptProps {
  isOpen: boolean;
  message: string;
  onConfirm: (password: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function PasswordPrompt({
  isOpen,
  message,
  onConfirm,
  onCancel,
  isLoading = false,
}: PasswordPromptProps) {
  const [password, setPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus sur l'input à l'ouverture
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 150);
      setPassword("");
      setError(null);
    }
  }, [isOpen]);

  // Soumission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("Veuillez entrer votre mot de passe");
      return;
    }
    setError(null);
    onConfirm(password.trim());
  };

  // Annulation
  const handleCancel = () => {
    setPassword("");
    setError(null);
    onCancel();
  };

  // ESC pour fermer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleCancel();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleCancel]);

  if (!isOpen) return null;

  return (
    <div className="pp-modal-overlay" onClick={handleCancel}>
      <div 
        className="pp-modal-box" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pp-modal-title"
      >
        {/* Header */}
        <div className="pp-modal-header">
          <div className="pp-modal-header__left">
            <div className="pp-modal-icon-wrapper">
              <ShieldCheck size={18} className="pp-modal-icon" />
            </div>
            <h3 id="pp-modal-title" className="pp-modal-title">
              Confirmation d'action sensible
            </h3>
          </div>
          <button 
            type="button" 
            className="pp-modal-close"
            onClick={handleCancel}
            aria-label="Fermer"
            disabled={isLoading}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="pp-modal-body">
          <p className="pp-modal-message">{message}</p>

          <form onSubmit={handleSubmit} className="pp-modal-form">
            <div className="pp-form-group">
              <label className="pp-form-label" htmlFor="pp-password-input">
                Mot de passe administrateur
              </label>
              <div className="pp-input-wrapper">
                <Lock size={16} className="pp-input-icon" />
                <input
                  id="pp-password-input"
                  ref={inputRef}
                  type={showPassword ? "text" : "password"}
                  className={`pp-form-input ${error ? "pp-form-input--error" : ""}`}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••"
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="pp-toggle-visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {error && <span className="pp-form-error">{error}</span>}
            </div>

            <div className="pp-form-actions">
              <button
                type="button"
                className="pp-btn pp-btn--secondary"
                onClick={handleCancel}
                disabled={isLoading}
              >
                Annuler
              </button>
              <button
                type="submit"
                className="pp-btn pp-btn--primary"
                disabled={isLoading || !password.trim()}
              >
                {isLoading ? (
                  <>
                    <span className="pp-spinner" /> Vérification...
                  </>
                ) : (
                  <>
                    <Lock size={14} /> Confirmer
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="pp-modal-footer">
          <span className="pp-modal-footer__text">
            Cette action est sécurisée et nécessite une authentification
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HOOK : usePasswordPrompt
// ============================================================================

import { useCallback } from "react";

type PasswordPromptHook = {
  prompt: (message: string) => Promise<string | null>;
  modal: any;
  isLoading: boolean;
};

export function usePasswordPrompt(
  onConfirmCallback?: (password: string) => void
): PasswordPromptHook {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const resolveRef = useRef<((value: string | null) => void) | null>(null);

  const prompt = useCallback((msg: string): Promise<string | null> => {
    setMessage(msg);
    setIsOpen(true);
    setIsLoading(false);
    return new Promise((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  const handleConfirm = async (password: string) => {
    setIsLoading(true);
    if (onConfirmCallback) {
      await onConfirmCallback(password);
    }
    setIsLoading(false);
    setIsOpen(false);
    if (resolveRef.current) {
      resolveRef.current(password);
      resolveRef.current = null;
    }
  };

  const handleCancel = () => {
    setIsOpen(false);
    if (resolveRef.current) {
      resolveRef.current(null);
      resolveRef.current = null;
    }
  };

  const modal = (
    <PasswordPrompt
      isOpen={isOpen}
      message={message}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
      isLoading={isLoading}
    />
  );

  return { prompt, modal, isLoading };
}

export default PasswordPrompt;