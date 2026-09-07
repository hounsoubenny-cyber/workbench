import "./theme_selector.css";
import { useEffect, useRef, useState } from "react";
import { Check, Moon, Sun, Waves, Palette, Flame, Ghost, Terminal } from "lucide-react";

export type ThemeName = "obsidian" | "daylight" | "aurora" | "ember" | "cyberpunk" | "dracula";

const THEME_STORAGE_KEY = "oh_theme";

const THEMES: { id: ThemeName; label: string; description: string; icon: typeof Moon; swatch: string[] }[] = [
  {
    id: "obsidian",
    label: "Obsidian",
    description: "Sombre studio, violet profond",
    icon: Moon,
    swatch: ["#090b10", "#7c6cf0", "#161a24"],
  },
  {
    id: "cyberpunk",
    label: "Cyberpunk",
    description: "Noir d'encre & vert terminal",
    icon: Terminal,
    swatch: ["#040806", "#00ff88", "#0f1a14"],
  },
  {
    id: "aurora",
    label: "Aurora",
    description: "Sarcelle nordique & bleu cyan",
    icon: Waves,
    swatch: ["#071018", "#14b8a6", "#122432"],
  },
  {
    id: "ember",
    label: "Ember",
    description: "Sombre cuivré & ambre chaud",
    icon: Flame,
    swatch: ["#120e0b", "#ea580c", "#221b15"],
  },
  {
    id: "dracula",
    label: "Dracula",
    description: "Violet-bleuté & rose néon",
    icon: Ghost,
    swatch: ["#1b1827", "#ff79c6", "#2b2640"],
  },
  {
    id: "daylight",
    label: "Daylight",
    description: "Clair technique et clinique",
    icon: Sun,
    swatch: ["#f4f6fa", "#4f46e5", "#ffffff"],
  },
];

export function getStoredTheme(): ThemeName {
  if (typeof window === "undefined") return "obsidian";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemeName | null;
  if (stored && THEMES.some((t) => t.id === stored)) return stored;
  return "obsidian";
}

export function applyTheme(theme: ThemeName) {
  document.documentElement.setAttribute("data-theme", theme);
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
}

function ThemeSelector() {
  const [theme, setTheme] = useState<ThemeName>(() => getStoredTheme());
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const activeTheme = THEMES.find((t) => t.id === theme) ?? THEMES[0];
  const ActiveIcon = activeTheme.icon;

  return (
    <div className="theme-selector" ref={wrapperRef}>
      <button
        type="button"
        className="theme-selector__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Choisir un thème"
        title="Choisir un thème"
      >
        <Palette size={16} className="theme-selector__trigger-icon" />
        <ActiveIcon size={16} />
        <span className="theme-selector__trigger-label">{activeTheme.label}</span>
      </button>

      {open && (
        <div className="theme-selector__panel" role="listbox">
          <div className="theme-selector__panel-title">Apparence</div>
          {THEMES.map((t) => {
            const Icon = t.icon;
            const active = t.id === theme;
            return (
              <button
                key={t.id}
                type="button"
                role="option"
                aria-selected={active}
                className={`theme-selector__option ${active ? "is-active" : ""}`}
                onClick={() => {
                  setTheme(t.id);
                  setOpen(false);
                }}
              >
                <span className="theme-selector__swatch" aria-hidden="true">
                  {t.swatch.map((color, i) => (
                    <span key={i} style={{ background: color }} />
                  ))}
                </span>
                <span className="theme-selector__option-text">
                  <span className="theme-selector__option-label">
                    <Icon size={14} />
                    {t.label}
                  </span>
                  <span className="theme-selector__option-desc">{t.description}</span>
                </span>
                {active && <Check size={16} className="theme-selector__check" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ThemeSelector;
