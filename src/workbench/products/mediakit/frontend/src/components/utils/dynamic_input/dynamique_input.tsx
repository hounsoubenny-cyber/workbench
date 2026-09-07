import React, { useState, useEffect, useId, useMemo, useCallback } from "react";
import "./dynamique_input.css";
import { ModelFieldMeta } from "@/types/types";
import { X, FileUp } from "lucide-react";

export type FieldSchema = ModelFieldMeta;

export interface DynamicInputProps {
  /** Nom de la clé du champ (ex: "input_file", "crf", "output_format") */
  fieldKey: string;
  /** Métadonnées du champ issues de model_to_dict */
  data: FieldSchema;
  /** Valeur courante injectée par le formulaire parent (optionnel) */
  value?: any;
  /** Callback déclenché à chaque modification */
  onSave: (key: string, value: any, file?: File | File[]) => void;
  disabled?: boolean;
}

const isNull = (val: any) => val === null || val === undefined;

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return "0 o";
  const k = 1024;
  const sizes = ["o", "Ko", "Mo", "Go"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

export const DynamicInput: React.FC<DynamicInputProps> = ({
  fieldKey,
  data,
  value,
  onSave,
  disabled = false,
}) => {
  const inputId = useId();

  // Détection upload et liste
  const isUpload = Boolean(data.is_upload ?? (data as any).isUpload);
  const isMultiple = String(data.type || "").startsWith("list");

  // Contraintes numériques & de taille
  const constraints = data.constraints || {};
  const minVal = constraints.ge ?? constraints.gt;
  const maxVal = constraints.le ?? constraints.lt;
  const minLength = constraints.min_length ?? (constraints as any).minLength;
  const maxLength = constraints.max_length ?? (constraints as any).maxLength;

  // Calcul de la valeur par défaut sécurisée
  const computeInitialValue = useCallback(() => {
    if (value !== undefined) return value;
    if (data.value !== undefined) return data.value;
    if (!isNull(data.default)) return data.default;
    if (data.type === "boolean") return false;
    if (data.type === "integer" || data.type === "float") return minVal ?? 0;
    if (data.choices && data.choices.length > 0) return data.choices[0];
    return "";
  }, [value, data, minVal]);

  const [currentVal, setCurrentVal] = useState<any>(computeInitialValue);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  useEffect(() => {
    if (value !== undefined) {
      setCurrentVal(value);
    }
  }, [value]);

  // ─── GESTIONNAIRES DE CHANGEMENT ──────────────────────────────────────────

  const handleTextOrNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawVal = e.target.value;
    let val: any = rawVal;

    if (data.type === "integer") {
      val = rawVal === "" ? "" : parseInt(rawVal, 10);
      if (isNaN(val)) val = "";
    } else if (data.type === "float") {
      // Autorise la saisie de "-" ou "1." sans bloquer l'utilisateur pendant qu'il tape
      if (rawVal === "" || rawVal === "-" || rawVal.endsWith(".")) {
        val = rawVal;
      } else {
        const parsed = parseFloat(rawVal);
        val = isNaN(parsed) ? "" : parsed;
      }
    } else {
      // 👈 CORRIGÉ : On conserve fidèlement le texte saisi par l'utilisateur !
      val = rawVal;
    }

    setCurrentVal(val);
    onSave(fieldKey, val);
  };

  const handleNumberBlur = () => {
    if (data.type === "integer" || data.type === "float") {
      let val = currentVal;

      // Si le champ est laissé vide ou invalide, on rétablit la valeur par défaut ou le min
      if (val === "" || val === "-" || isNaN(Number(val))) {
        val = !isNull(data.default) ? data.default : minVal ?? 0;
      } else {
        val = Number(val);
        // Bornage automatique aux limites autorisées
        if (!isNull(minVal) && val < minVal) val = minVal;
        if (!isNull(maxVal) && val > maxVal) val = maxVal;
      }

      setCurrentVal(val);
      onSave(fieldKey, val);
    }
  };

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setCurrentVal(val);
    onSave(fieldKey, val);
  };

  const handleBooleanToggle = () => {
    if (disabled) return;
    const nextVal = !currentVal;
    setCurrentVal(nextVal);
    onSave(fieldKey, nextVal);
  };

  const processFiles = (filesArray: File[]) => {
    if (filesArray.length === 0) return;

    if (isMultiple) {
      setSelectedFiles(filesArray);
      const fileNames = filesArray.map((f) => f.name);
      setCurrentVal(fileNames);
      onSave(fieldKey, fileNames, filesArray);
    } else {
      const singleFile = filesArray[0];
      setSelectedFiles([singleFile]);
      setCurrentVal(singleFile.name);
      onSave(fieldKey, singleFile.name, singleFile);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    processFiles(Array.from(files));
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      processFiles(Array.from(files));
    }
  };

  const removeFile = (index: number) => {
    if (disabled) return;
    const updated = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(updated);

    if (isMultiple) {
      const names = updated.map((f) => f.name);
      setCurrentVal(names);
      onSave(fieldKey, names, updated);
    } else {
      setCurrentVal("");
      onSave(fieldKey, "", []);
    }
  };

  // ─── RENDU DU CONTRÔLE ───────────────────────────────────────────────────

  const renderControl = () => {
    // 1. CHAMP D'UPLOAD (UploadRef)
    if (isUpload) {
      return (
        <div className="wb-dyn-upload">
          <label
            htmlFor={inputId}
            onDragOver={(e) => {
              e.preventDefault();
              if (!disabled) setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            className={`wb-dyn-upload__dropzone ${
              isDragOver ? "wb-dyn-upload__dropzone--active" : ""
            } ${disabled ? "wb-dyn-upload__dropzone--disabled" : ""}`}
          >
            <svg
              className="wb-dyn-upload__icon"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.75"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>

            <span className="wb-dyn-upload__primary-text">
              {selectedFiles.length > 0
                ? isMultiple
                  ? `${selectedFiles.length} fichier(s) prêt(s)`
                  : selectedFiles[0].name
                : isMultiple
                ? "Parcourir ou déposer plusieurs fichiers"
                : "Parcourir ou déposer un fichier"}
            </span>

            <span className="wb-dyn-upload__subtext">
              {isMultiple
                ? "Sélection multiple autorisée"
                : "Glissez-déposez ou cliquez ici"}
            </span>

            <input
              id={inputId}
              type="file"
              multiple={isMultiple}
              disabled={disabled}
              onChange={handleFileChange}
              className="wb-dyn-upload__input-hidden"
            />
          </label>

          {/* Liste récapitulative des fichiers sélectionnés avec bouton supprimer */}
          {selectedFiles.length > 0 && (
            <div className="wb-dyn-upload__file-list">
              {selectedFiles.map((file, i) => (
                <span key={`${file.name}-${i}`} className="wb-dyn-upload__file-chip">
                  <span className="wb-dyn-upload__file-name">{file.name}</span>
                  <span className="wb-dyn-upload__file-meta">
                    {formatFileSize(file.size)}
                  </span>
                  {!disabled && (
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      className="wb-dyn-upload__file-remove"
                      title="Retirer ce fichier"
                    >
                      <X size={12} />
                    </button>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    // 2. ÉNUMÉRATION / CHOIX (Dropdown <select>)
    if (data.type === "enum" || (data.choices && data.choices.length > 0)) {
      return (
        <select
          id={inputId}
          value={currentVal}
          disabled={disabled}
          onChange={handleSelectChange}
          className="wb-dyn-select"
        >
          {data.choices?.map((choice) => (
            <option key={String(choice)} value={String(choice)}>
              {String(choice)}
            </option>
          ))}
        </select>
      );
    }

    // 3. BOOLÉEN (Toggle Switch)
    if (data.type === "boolean") {
      const isChecked = Boolean(currentVal);
      return (
        <div className="wb-dyn-toggle-wrapper">
          <button
            type="button"
            role="switch"
            id={inputId}
            aria-checked={isChecked}
            disabled={disabled}
            onClick={handleBooleanToggle}
            className={`wb-dyn-toggle ${
              isChecked ? "wb-dyn-toggle--checked" : ""
            } ${disabled ? "wb-dyn-toggle--disabled" : ""}`}
          >
            <span className="wb-dyn-toggle__thumb" />
          </button>
          <span className="wb-dyn-toggle__label">
            {isChecked ? "Activé (True)" : "Désactivé (False)"}
          </span>
        </div>
      );
    }

    // 4. NOMBRE (Integer ou Float avec min/max/step)
    if (data.type === "integer" || data.type === "float") {
      const step = data.type === "integer" ? 1 : 0.1;

      return (
        <div className="wb-dyn-number-wrapper">
          <input
            id={inputId}
            type="number"
            value={currentVal}
            step={step}
            min={minVal}
            max={maxVal}
            disabled={disabled}
            onChange={handleTextOrNumberChange}
            onBlur={handleNumberBlur}
            className="wb-dyn-input"
          />
          {(minVal !== undefined || maxVal !== undefined) && (
            <span className="wb-dyn-bounds">
              [{minVal ?? "-∞"} à {maxVal ?? "+∞"}]
            </span>
          )}
        </div>
      );
    }

    // 5. CHAMP TEXTE PAR DÉFAUT (String, PatternArg...)
    return (
      <input
        id={inputId}
        type="text"
        value={currentVal}
        disabled={disabled}
        minLength={minLength}
        maxLength={maxLength}
        placeholder={!isNull(data.default) ? String(data.default) : ""}
        onChange={handleTextOrNumberChange}
        className="wb-dyn-input"
      />
    );
  };

  // ─── RENDU DU CHAMP ───────────────────────────────────────────────────────

  return (
    <div className="wb-dyn-field">
      <div className="wb-dyn-field__header">
        <label htmlFor={inputId} className="wb-dyn-field__label">
          {data.name}
          {data.required && <span className="wb-dyn-field__required">*</span>}
        </label>
        <span className="wb-dyn-field__type-badge">{data.type}</span>
      </div>

      <div className="wb-dyn-field__control">{renderControl()}</div>

      {data.description && (
        <p className="wb-dyn-field__description">{data.description}</p>
      )}
    </div>
  );
};

export default DynamicInput;