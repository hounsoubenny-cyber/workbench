import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  ReactNode,
} from "react";
import "./toast.css";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastOptions {
  description?: string;
  emoji?: string;
  duration?: number;
}

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  emoji?: string;
  duration: number;
}

interface ToastContextType {
  success: (title: string, options?: ToastOptions) => void;
  error: (title: string, options?: ToastOptions) => void;
  warning: (title: string, options?: ToastOptions) => void;
  info: (title: string, options?: ToastOptions) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [isHovered, setIsHovered] = useState(false);
  const idCounter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, title: string, options: ToastOptions = {}) => {
      idCounter.current += 1;
      const id = `wb-toast-${Date.now()}-${idCounter.current}`;
      const duration = options.duration ?? 4000;

      const defaultEmojis: Record<ToastType, string> = {
        success: "✨",
        error: "💥",
        warning: "⚠️",
        info: "💡",
      };

      const newToast: ToastItem = {
        id,
        type,
        title,
        description: options.description,
        emoji: options.emoji || defaultEmojis[type],
        duration,
      };

      setToasts((prev) => {
        // Déduplication : empêche d'ajouter le même toast s'il est déjà en haut
        const isDuplicate = prev.some(
          (t) => t.title === title && t.description === options.description
        );
        if (isDuplicate) return prev;

        // On garde au maximum les 4 plus récents
        const updated = [newToast, ...prev];
        return updated.slice(0, 4);
      });

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider
      value={{
        success: (t, o) => addToast("success", t, o),
        error: (t, o) => addToast("error", t, o),
        warning: (t, o) => addToast("warning", t, o),
        info: (t, o) => addToast("info", t, o),
        dismiss,
      }}
    >
      {children}

      {/* Conteneur flottant en bas ou haut droite avec cartes empilées */}
      <div
        className={`wb-toast-stack ${isHovered ? "is-expanded" : ""}`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        aria-live="polite"
      >
        {toasts.map((t, index) => {
          // Calcul de la profondeur et du décalage (carte 0 devant, 1 derrière, 2 encore derrière)
          const offset = index * 10;
          const scale = 1 - index * 0.05;
          const opacity = index > 2 ? 0 : 1 - index * 0.18;
          const zIndex = 50 - index;

          return (
            <div
              key={t.id}
              className={`wb-toast wb-toast--${t.type}`}
              style={{
                transform: isHovered
                  ? `translateY(${index * 76}px) scale(1)`
                  : `translateY(${offset}px) scale(${scale})`,
                zIndex,
                opacity,
              }}
              role="alert"
            >
              <div className="wb-toast__badge">
                <span className="wb-toast__emoji">{t.emoji}</span>
                {t.type === "success" && <CheckCircle2 size={15} className="wb-toast__icon" />}
                {t.type === "error" && <AlertCircle size={15} className="wb-toast__icon" />}
                {t.type === "warning" && <AlertTriangle size={15} className="wb-toast__icon" />}
                {t.type === "info" && <Info size={15} className="wb-toast__icon" />}
              </div>

              <div className="wb-toast__content">
                <h5 className="wb-toast__title">{t.title}</h5>
                {t.description && <p className="wb-toast__desc">{t.description}</p>}
              </div>

              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="wb-toast__close"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
};