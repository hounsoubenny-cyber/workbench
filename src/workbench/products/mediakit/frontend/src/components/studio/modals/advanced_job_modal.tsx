import React, { useState } from "react";
import "./job_create_modal.css";
import {
  RawEntry,
  RawArg,
  ArgTypeEnum,
  MultiPathMode,
  CreateJobResponse,
  ToolName,
} from "@/types/types";
import { launchAdvancedJob } from "@/hooks/utils";
import { useToast } from "@/components/utils/toast/toast_context";
import {
  X,
  Play,
  Terminal,
  Plus,
  Trash2,
  Clock,
  Sliders,
  Upload,
  FileCode,
  FileUp,
} from "lucide-react";

interface AdvancedJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onJobCreated: (job: CreateJobResponse) => void;
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 o";
  const k = 1024;
  const sizes = ["o", "Ko", "Mo", "Go"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

interface ArgWithFile extends RawArg {
  _file?: File;
  _raw_enum?: string;
  _raw_multipath?: string;
}

export const AdvancedJobModal: React.FC<AdvancedJobModalProps> = ({
  isOpen,
  onClose,
  onJobCreated,
}) => {
  const toast = useToast();

  // 1. Moteur & Fichier de sortie
  const [tool, setTool] = useState<ToolName>("ffmpeg");
  const [outputFilename, setOutputFilename] = useState<string>("output.mp4");

  // 2. Options d'exécution
  const [checkVersion, setCheckVersion] = useState<boolean>(true);
  const [minVersionStr, setMinVersionStr] = useState<string>("");
  const [captureStdout, setCaptureStdout] = useState<boolean>(false);
  const [timeout, setTimeoutSeconds] = useState<number>(300);

  // 3. Arguments CLI
  const [args, setArgs] = useState<ArgWithFile[]>([
    {
      type: "path" as ArgTypeEnum,
      flag: "-i",
      value: "input.mp4",
      must_exist: true,
      is_upload_file: true,
    },
    {
      type: "pattern" as ArgTypeEnum,
      flag: "-c:v",
      value: "libx264",
    },
  ]);

  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleToolChange = (newTool: ToolName) => {
    setTool(newTool);
    if (newTool === "ffmpeg") setOutputFilename("output.mp4");
    else if (newTool === "sox") setOutputFilename("output.wav");
    else if (newTool === "magick") setOutputFilename("output.webp");
  };

  const addArg = () => {
    setArgs((prev) => [
      ...prev,
      {
        type: "pattern" as ArgTypeEnum,
        flag: "",
        value: "",
      },
    ]);
  };

  const removeArg = (index: number) => {
    setArgs((prev) => prev.filter((_, i) => i !== index));
  };

  const updateArg = (index: number, partial: Partial<ArgWithFile>) => {
    setArgs((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...partial };
      return copy;
    });
  };

  // Sélection d'un fichier lié directement à un argument Path
  const handleFileForArg = (index: number, file: File) => {
    updateArg(index, {
      _file: file,
      value: file.name, // Met à jour automatiquement le nom attendu sur disque
      is_upload_file: true,
      must_exist: true,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;

    let parsedMinVersion: [number, number, number?] | null = null;
    if (checkVersion && minVersionStr.trim()) {
      const parts = minVersionStr
        .split(".")
        .map((p) => parseInt(p.trim(), 10))
        .filter((n) => !isNaN(n));
      if (parts.length >= 2) {
        parsedMinVersion = [parts[0], parts[1], parts[2]];
      }
    }

    // Récupère les fichiers dans l'ordre exact des arguments ayant is_upload_file
    const filesToUpload: File[] = [];
    const sanitizedArgs: RawArg[] = args.map((arg) => {
      const { _file, _raw_enum, _raw_multipath, ...cleanArg } = arg;

      if (cleanArg.is_upload_file && _file) {
        filesToUpload.push(_file);
      }

      if (cleanArg.type === "int") {
        cleanArg.value = parseInt(String(cleanArg.value), 10) || 0;
        cleanArg.min_value = cleanArg.min_value !== undefined && cleanArg.min_value !== null ? Number(cleanArg.min_value) : undefined;
        cleanArg.max_value = cleanArg.max_value !== undefined && cleanArg.max_value !== null ? Number(cleanArg.max_value) : undefined;
      } else if (cleanArg.type === "float") {
        cleanArg.value = parseFloat(String(cleanArg.value)) || 0;
        cleanArg.min_value = cleanArg.min_value !== undefined && cleanArg.min_value !== null ? Number(cleanArg.min_value) : undefined;
        cleanArg.max_value = cleanArg.max_value !== undefined && cleanArg.max_value !== null ? Number(cleanArg.max_value) : undefined;
      } else if (cleanArg.type === "bool") {
        cleanArg.value = Boolean(cleanArg.value);
      } else if (cleanArg.type === "enum") {
        if (typeof _raw_enum === "string") {
          cleanArg.enum_values = _raw_enum.split(",").map((s) => s.trim()).filter(Boolean);
        }
      } else if (cleanArg.type === "multi_path") {
        if (typeof _raw_multipath === "string") {
          cleanArg.values = _raw_multipath.split(",").map((s) => s.trim()).filter(Boolean);
        }
      }
      return cleanArg;
    });

    const rawEntry: RawEntry = {
      tool,
      output_filename: outputFilename,
      capture_stdout: captureStdout,
      timeout,
      check_version: checkVersion,
      min_version: parsedMinVersion,
      args: sanitizedArgs,
    };

    let launchError: string | null = null;
    const result = await launchAdvancedJob(
      rawEntry,
      filesToUpload,
      null,
      (err) => {
        launchError = err;
      },
      setSubmitting
    );

    if (result) {
      toast.success("Job personnalisé lancé !", {
        emoji: "⚡",
        description: `Commande manuelle envoyée au moteur ${tool}.`,
      });
      onJobCreated(result);
      onClose();
    } else {
      toast.error("Erreur commande manuelle", {
        emoji: "💥",
        description: launchError || "Vérifiez vos flags et arguments CLI.",
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="wb-job-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="wb-job-modal wb-job-modal--advanced">
        {/* En-tête */}
        <div className="wb-job-modal__header">
          <div className="wb-job-modal__title-group">
            <span className="wb-badge wb-badge--warning">
              <Terminal size={13} /> Mode Manuel (RawEntry)
            </span>
            <h3 className="wb-job-modal__title">Créer une commande CLI personnalisée</h3>
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

        <form onSubmit={handleSubmit} className="wb-job-modal__form">
          <div className="wb-job-modal__body">
            {/* 1. Moteur CLI & Fichier de sortie */}
            <div className="wb-raw-section">
              <div className="wb-raw-grid-2">
                <div className="wb-dyn-field">
                  <label className="wb-dyn-field__label">Moteur CLI Cible 🛠️</label>
                  <select
                    value={tool}
                    onChange={(e) => handleToolChange(e.target.value as ToolName)}
                    className="wb-select"
                  >
                    <option value="ffmpeg">FFmpeg (Vidéo / Audio) 🎬</option>
                    <option value="sox">SoX (Audio DSP Studio) 🎚️</option>
                    <option value="magick">ImageMagick (Image) 🎨</option>
                  </select>
                </div>

                <div className="wb-dyn-field">
                  <label className="wb-dyn-field__label">Nom du fichier produit</label>
                  <input
                    type="text"
                    value={outputFilename}
                    onChange={(e) => setOutputFilename(e.target.value)}
                    className="wb-input"
                    placeholder="ex: rendered.mp4"
                    required
                  />
                </div>
              </div>
            </div>

            {/* 2. Options d'exécution & Vérifications */}
            <div className="wb-raw-section wb-raw-section--options">
              <div className="wb-raw-section-title">
                <Sliders size={14} />
                <span>Options Système & Vérifications</span>
              </div>

              <div className="wb-raw-options-grid">
                <div className="wb-raw-option-item">
                  <div className="wb-dyn-toggle-wrapper">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={checkVersion}
                      onClick={() => setCheckVersion(!checkVersion)}
                      className={`wb-dyn-toggle ${checkVersion ? "wb-dyn-toggle--checked" : ""}`}
                    >
                      <span className="wb-dyn-toggle__thumb" />
                    </button>
                    <span className="wb-dyn-toggle__label">
                      Vérifier la version du binaire (<code>check_version</code>)
                    </span>
                  </div>

                  {checkVersion && (
                    <div className="wb-raw-min-version-box">
                      <input
                        type="text"
                        placeholder="Min (ex: 4.0)"
                        value={minVersionStr}
                        onChange={(e) => setMinVersionStr(e.target.value)}
                        className="wb-input wb-raw-min-version-input"
                      />
                      <span className="hint">min_version</span>
                    </div>
                  )}
                </div>

                <div className="wb-raw-option-item">
                  <div className="wb-dyn-toggle-wrapper">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={captureStdout}
                      onClick={() => setCaptureStdout(!captureStdout)}
                      className={`wb-dyn-toggle ${captureStdout ? "wb-dyn-toggle--checked" : ""}`}
                    >
                      <span className="wb-dyn-toggle__thumb" />
                    </button>
                    <span className="wb-dyn-toggle__label">
                      Capturer <code>stdout</code> dans le fichier de sortie
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Constructeur Dynamique d'Arguments */}
            <div className="wb-raw-section">
              <div className="wb-raw-section-header">
                <span className="wb-raw-section-title">
                  <FileCode size={14} /> Arguments de commande (ArgTypés) :
                </span>
                <button
                  type="button"
                  onClick={addArg}
                  className="wb-btn wb-btn--ghost wb-raw-add-btn"
                >
                  <Plus size={13} /> Ajouter un Argument
                </button>
              </div>

              <div className="wb-raw-args-stack">
                {args.map((arg, idx) => (
                  <div key={idx} className="wb-raw-arg-card">
                    {/* Ligne 1 : Grille rigide (Index | Type | Flag | Poubelle) */}
                    <div className="wb-raw-arg-card__grid-header">
                      <span className="wb-raw-arg-index">#{idx + 1}</span>

                      <select
                        value={arg.type}
                        onChange={(e) => {
                          const newType = e.target.value as ArgTypeEnum;
                          updateArg(idx, {
                            type: newType,
                            value: newType === "bool" ? true : "",
                            min_value: undefined,
                            max_value: undefined,
                            must_exist: newType === "path",
                            is_upload_file: newType === "path",
                            _file: undefined,
                          });
                        }}
                        className="wb-select wb-raw-type-select"
                      >
                        <option value="path">📁 Chemin (Path)</option>
                        <option value="pattern">🔤 Motif / Filtre (Pattern)</option>
                        <option value="int">🔢 Entier (Int)</option>
                        <option value="float">📐 Flottant (Float)</option>
                        <option value="bool">🔘 Booléen (Bool)</option>
                        <option value="enum">📑 Choix fermés (Enum)</option>
                        <option value="multi_path">📚 Multi-chemins (MultiPath)</option>
                      </select>

                      <input
                        type="text"
                        placeholder="Flag (ex: -i, -crf ou vide si positionnel)"
                        value={arg.flag}
                        onChange={(e) => updateArg(idx, { flag: e.target.value })}
                        className="wb-input wb-raw-flag-input"
                      />

                      <button
                        type="button"
                        onClick={() => removeArg(idx)}
                        className="wb-raw-del-btn"
                        title="Supprimer cet argument"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    {/* Ligne 2 : Champs dynamiques selon le type */}
                    <div className="wb-raw-arg-card__body">
                      {/* TYPE PATH AVEC SÉLECTION FICHIER DIRECTE */}
                      {arg.type === "path" && (
                        <div className="wb-raw-path-row">
                          <div className="path-input-group">
                            <label className="wb-raw-sublabel">
                              Nom dans le workdir (utilisé par la CLI) :
                            </label>
                            <input
                              type="text"
                              placeholder="ex: input.mp4"
                              value={arg.value ?? ""}
                              onChange={(e) => updateArg(idx, { value: e.target.value })}
                              className="wb-input"
                              required
                            />
                          </div>

                          <div className="path-file-picker">
                            <label className="wb-raw-sublabel">Fichier source local :</label>
                            <label className="wb-raw-mini-upload">
                              <FileUp size={14} />
                              <span>{arg._file ? arg._file.name : "Parcourir..."}</span>
                              <input
                                type="file"
                                className="hidden"
                                onChange={(e) => {
                                  if (e.target.files && e.target.files[0]) {
                                    handleFileForArg(idx, e.target.files[0]);
                                  }
                                }}
                              />
                            </label>
                          </div>

                          <div className="wb-raw-checkboxes">
                            <label className="wb-raw-checkbox-label">
                              <input
                                type="checkbox"
                                checked={Boolean(arg.must_exist)}
                                onChange={(e) => updateArg(idx, { must_exist: e.target.checked })}
                              />
                              <span>must_exist (Fichier source requis)</span>
                            </label>
                            <label className="wb-raw-checkbox-label">
                              <input
                                type="checkbox"
                                checked={Boolean(arg.is_upload_file)}
                                onChange={(e) => updateArg(idx, { is_upload_file: e.target.checked })}
                              />
                              <span>is_upload_file (Envoyé au serveur)</span>
                            </label>
                            {arg._file && (
                              <span className="file-ready-tag">
                                Prêt ({formatFileSize(arg._file.size)})
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* TYPE INT / FLOAT */}
                      {(arg.type === "int" || arg.type === "float") && (
                        <div className="wb-raw-number-grid">
                          <div className="num-col">
                            <label className="wb-raw-sublabel">Valeur :</label>
                            <input
                              type="number"
                              step={arg.type === "int" ? 1 : 0.1}
                              value={arg.value ?? ""}
                              onChange={(e) => updateArg(idx, { value: e.target.value })}
                              placeholder="ex: 24"
                              className="wb-input"
                              required
                            />
                          </div>

                          <div className="num-col">
                            <label className="wb-raw-sublabel">Min autorisé (opt) :</label>
                            <input
                              type="number"
                              value={arg.min_value ?? ""}
                              onChange={(e) =>
                                updateArg(idx, {
                                  min_value: e.target.value === "" ? undefined : Number(e.target.value),
                                })
                              }
                              placeholder="min_value"
                              className="wb-input"
                            />
                          </div>

                          <div className="num-col">
                            <label className="wb-raw-sublabel">Max autorisé (opt) :</label>
                            <input
                              type="number"
                              value={arg.max_value ?? ""}
                              onChange={(e) =>
                                updateArg(idx, {
                                  max_value: e.target.value === "" ? undefined : Number(e.target.value),
                                })
                              }
                              placeholder="max_value"
                              className="wb-input"
                            />
                          </div>
                        </div>
                      )}

                      {/* TYPE BOOL */}
                      {arg.type === "bool" && (
                        <div className="wb-raw-bool-box">
                          <div className="wb-dyn-toggle-wrapper">
                            <button
                              type="button"
                              role="switch"
                              aria-checked={Boolean(arg.value)}
                              onClick={() => updateArg(idx, { value: !arg.value })}
                              className={`wb-dyn-toggle ${arg.value ? "wb-dyn-toggle--checked" : ""}`}
                            >
                              <span className="wb-dyn-toggle__thumb" />
                            </button>
                            <span className="wb-dyn-toggle__label">
                              {arg.value
                                ? `Actif : le flag "${arg.flag || "(flag vide)"}" sera inclus`
                                : `Inactif : le flag sera omis`}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* TYPE ENUM */}
                      {arg.type === "enum" && (
                        <div className="wb-raw-enum-grid">
                          <div className="num-col">
                            <label className="wb-raw-sublabel">Valeur retenue :</label>
                            <input
                              type="text"
                              placeholder="ex: libx264"
                              value={arg.value ?? ""}
                              onChange={(e) => updateArg(idx, { value: e.target.value })}
                              className="wb-input"
                              required
                            />
                          </div>
                          <div className="num-col">
                            <label className="wb-raw-sublabel">Choix autorisés (séparés par virgule) :</label>
                            <input
                              type="text"
                              placeholder="ex: libx264, libx265, vp9"
                              value={arg._raw_enum ?? arg.enum_values?.join(", ") ?? ""}
                              onChange={(e) => updateArg(idx, { _raw_enum: e.target.value })}
                              className="wb-input"
                              required
                            />
                          </div>
                        </div>
                      )}

                      {/* TYPE PATTERN */}
                      {arg.type === "pattern" && (
                        <div className="wb-raw-field-group">
                          <label className="wb-raw-sublabel">Chaîne / Expression :</label>
                          <input
                            type="text"
                            placeholder="ex: scale=1280:-1 ou fps=30"
                            value={arg.value ?? ""}
                            onChange={(e) => updateArg(idx, { value: e.target.value })}
                            className="wb-input"
                            required
                          />
                        </div>
                      )}

                      {/* TYPE MULTI_PATH */}
                      {arg.type === "multi_path" && (
                        <div className="wb-raw-multipath-box">
                          <div className="mp-header-row">
                            <div className="num-col flex-1">
                              <label className="wb-raw-sublabel">Mode de répétition CLI :</label>
                              <select
                                value={arg.mode || "repeat_flag"}
                                onChange={(e) => updateArg(idx, { mode: e.target.value as MultiPathMode })}
                                className="wb-select"
                              >
                                <option value="repeat_flag">Répéter le flag (-i f1 -i f2)</option>
                                <option value="positional">Positionnel sans répétition (f1 f2)</option>
                                <option value="joined">Joint avec séparateur (--files f1,f2)</option>
                              </select>
                            </div>
                            {arg.mode === "joined" && (
                              <div className="num-col" style={{ width: "80px" }}>
                                <label className="wb-raw-sublabel">Séparateur :</label>
                                <input
                                  type="text"
                                  value={arg.separator ?? ","}
                                  onChange={(e) => updateArg(idx, { separator: e.target.value })}
                                  className="wb-input text-center"
                                />
                              </div>
                            )}
                          </div>

                          <div className="num-col">
                            <label className="wb-raw-sublabel">Noms des fichiers (séparés par virgule) :</label>
                            <input
                              type="text"
                              placeholder="part1.mp4, part2.mp4, part3.mp4"
                              value={arg._raw_multipath ?? arg.values?.join(", ") ?? ""}
                              onChange={(e) => updateArg(idx, { _raw_multipath: e.target.value })}
                              className="wb-input"
                              required
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 4. Timeout global */}
            <div className="wb-job-modal__timeout-row">
              <label htmlFor="adv_timeout" className="wb-job-modal__timeout-label">
                <Clock size={14} />
                <span>Temps limite d'exécution (Timeout) :</span>
              </label>
              <div className="wb-job-modal__timeout-input-group">
                <input
                  id="adv_timeout"
                  type="number"
                  min={10}
                  max={3600}
                  step={10}
                  value={timeout}
                  disabled={submitting}
                  onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                  className="wb-input wb-job-modal__timeout-input"
                />
                <span>secondes ⏱️</span>
              </div>
            </div>
          </div>

          {/* Pied de page fixe */}
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
              disabled={submitting}
              className="wb-btn wb-btn--primary"
            >
              <Play size={14} fill="currentColor" />
              <span>{submitting ? "Exécution en cours... ⏳" : "Lancer la commande CLI 🚀"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};