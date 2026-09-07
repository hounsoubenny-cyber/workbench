import {
  WbConfig,
  UpdateConfigData,
  FullCatalogResponse,
  SpecInfoResponse,
  CreateJobResponse,
  JobStatusResponse,
  JobStopResponse,
  BinaryCheckResponse,
  ApiStatusResponse,
  RawEntry,
  ToolName,
  ErrorCode,
} from "@/types/types";

import {
  getBackendConfig,
  setBackendConfig,
  getBackendCatalog,
  getBackendSpecInfo,
  createBackendJob,
  createAdvancedBackendJob,
  getBackendJobStatus,
  stopBackendJob,
  checkBackendBinary,
  getBackendStatus,
  downloadBackendFile,
} from "./fetch_functions";
import { logError } from "./error_utils";
import { _FetchResult } from "./fetch_functions_bases";

// ============================================================================
// GESTIONNAIRE & TRADUCTEUR D'ERREURS CENTRALISÉ (HTTP & ERROR_CODE)
// ============================================================================

export function resolveApiError(result: _FetchResult<any>): string {
  if (result.ok) return "";

  const status = result.status;
  const rawResponse = result.response as Record<string, any> | null;
  const detail = rawResponse?.detail;

  // 1. Si le backend a renvoyé un objet structuré via error_mapper.py
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const errorCode = detail.error_code as ErrorCode | undefined;
    const message = detail.message as string | undefined;

    if (message) return message;

    switch (errorCode) {
      case "TOO_MANY_JOBS":
        return "Le serveur est saturé : trop de conversions tournent simultanément. Réessayez dans un instant.";
      case "JOB_ALREADY_EXISTS":
        return "Conflit : une tâche avec cet identifiant est déjà en cours.";
      case "FORBIDDEN_PATH":
        return "Accès interdit : tentative de sortie de l'espace de travail sécurisé.";
      case "FILE_NOT_FOUND":
        return "Le fichier source requis est introuvable ou a été nettoyé.";
      case "TOOL_MISSING":
        return "Outil introuvable : le binaire CLI nécessaire n'est pas installé sur la machine.";
      case "TOOL_UNVERIFIED":
        return "Alerte de sécurité : l'exécutable système est suspect ou non officiel.";
      case "TOOL_VERSION_INCOMPATIBLE":
        return "Version incompatible : la version de l'outil installée est obsolète.";
      case "JOB_TIMEOUT":
        return "Temps limite dépassé : le traitement a pris trop de temps et a été stoppé.";
      case "JOB_CANCELLED":
        return "La tâche a été annulée.";
      case "UPLOAD_COUNT_MISMATCH":
        return "Erreur d'upload : le nombre de fichiers transmis ne correspond pas à la demande.";
      case "DUPLICATE_UPLOAD_NAME":
        return "Noms de fichiers en double dans la sélection.";
      case "INVALID_UPLOAD_NAME":
        return "Nom de fichier invalide ou caractères interdits.";
      case "VALIDATION_BUSINESS_ERROR":
        return "Validation échouée : le fichier fourni ne respecte pas les critères requis.";
      case "INVALID_INPUT_PARAMS":
        return "Paramètres invalides : veuillez vérifier les valeurs saisies dans le formulaire.";
      case "INVALID_ARGUMENT":
        return "Argument invalide pour cet outil.";
      case "PIPELINE_STEP_FAILED":
        return "Une étape intermédiaire du pipeline a échoué.";
      case "NO_AUDIO_STREAM_FOUND":
        return "La vidéo source ne contient aucune piste audio à extraire.";
      default:
        break;
    }
  }

  // 2. Si detail est une chaîne brute
  if (typeof detail === "string") {
    if (detail === "INVALID_WORKDIR") return "Dossier de travail du job non reconnu ou expiré.";
    if (detail === "FORBIDDEN_PATH") return "Accès refusé : chemin de fichier non autorisé.";
    return detail;
  }

  // 3. Fallback selon le code de statut HTTP
  switch (status) {
    case 400:
      return "Requête invalide : paramètres incorrects.";
    case 403:
      return "Action non autorisée sur ce fichier.";
    case 404:
      return "Ressource, fichier ou action introuvable.";
    case 406:
      return "Format de dossier ou de fichier inacceptable.";
    case 409:
      return "Conflit d'état du job sur le serveur.";
    case 422:
      return "Erreur de validation des données fournies.";
    case 429:
      return "Trop de requêtes ou serveur saturé.";
    case 500:
      return "Erreur interne du moteur CLI.";
    case 503:
      return "Outil CLI manquant ou service temporairement indisponible.";
    case 504:
      return "Le serveur n'a pas répondu à temps (Timeout).";
    default:
      return result.error || "Une erreur inattendue de communication avec le serveur est survenue.";
  }
}

// ============================================================================
// 1. CONFIGURATION DU SERVEUR
// ============================================================================

export async function fetchServerConfig(
  setResult: ((val: WbConfig | null) => void) | null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<WbConfig | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await getBackendConfig();
    if (result.ok && result.response) {
      const data = result.response as WbConfig;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function updateServerConfig(
  data: UpdateConfigData | WbConfig,
  setResult: ((val: { success: boolean } | null) => void) | null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<boolean> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await setBackendConfig(data);
    if (result.ok && result.response) {
      const resp = result.response as { success: boolean };
      if (setResult) setResult(resp);
      return resp.success;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return false;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}

// ============================================================================
// 2. CATALOGUE DES OUTILS & INTROSPECTION DE SPECS
// ============================================================================

export async function fetchCatalog(
  setResult: ((val: FullCatalogResponse | null) => void) | null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<FullCatalogResponse | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await getBackendCatalog();
    if (result.ok && result.response) {
      const data = result.response as FullCatalogResponse;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function fetchSpecInfo(
  specId: string,
  setResult: ((val: SpecInfoResponse | null) => void) | null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<SpecInfoResponse | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await getBackendSpecInfo(specId);
    if (result.ok && result.response) {
      const data = result.response as SpecInfoResponse;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

// ============================================================================
// 3. LANCEMENT & GESTION DES JOBS
// ============================================================================

export async function launchCatalogJob(
  specId: string,
  userInput: Record<string, any>,
  files: (File | Blob)[] = [],
  timeout: number | null = null,
  setResult: ((val: CreateJobResponse | null) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<CreateJobResponse | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await createBackendJob(specId, userInput, files, timeout);
    if (result.ok && result.response) {
      const data = result.response as CreateJobResponse;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function launchAdvancedJob(
  rawEntry: RawEntry | Record<string, any>,
  files: (File | Blob)[] = [],
  setResult: ((val: CreateJobResponse | null) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<CreateJobResponse | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await createAdvancedBackendJob(rawEntry, files);
    if (result.ok && result.response) {
      const data = result.response as CreateJobResponse;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function fetchJobStatus(
  jobId: string,
  setResult: ((val: JobStatusResponse | null) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<JobStatusResponse | null> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await getBackendJobStatus(jobId);
    if (result.ok && result.response) {
      const data = result.response as JobStatusResponse;
      if (setResult) setResult(data);
      return data;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return null;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return null;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function cancelJob(
  jobId: string,
  setResult: ((val: JobStopResponse | null) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<boolean> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await stopBackendJob(jobId);
    if (result.ok && result.response) {
      const data = result.response as JobStopResponse;
      if (setResult) setResult(data);
      return data.success;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(null);
    return false;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}

// ============================================================================
// 4. SYSTÈME & VÉRIFICATION DES BINAIRES
// ============================================================================

export async function verifyToolInstalled(
  toolName: ToolName | string,
  setResult: ((val: boolean) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<boolean> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await checkBackendBinary(toolName);
    if (result.ok && result.response) {
      const isFound = Boolean((result.response as BinaryCheckResponse).find);
      if (setResult) setResult(isFound);
      return isFound;
    }

    const err = resolveApiError(result);
    setError(err);
    if (setResult) setResult(false);
    return false;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    if (setResult) setResult(false);
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}

export async function checkBackendHealth(
  setResult: ((val: boolean) => void) | null = null,
  setError: (err: string | null) => void,
  setLoading: ((loading: boolean) => void) | null = null
): Promise<boolean> {
  try {
    if (setLoading) setLoading(true);
    setError(null);

    const result = await getBackendStatus();
    const isOk = result.ok && (result.response as ApiStatusResponse)?.status === "ok";
    if (setResult) setResult(isOk);
    return isOk;
  } catch (err: any) {
    const msg = logError(err);
    setError(msg);
    if (setResult) setResult(false);
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}

// ============================================================================
// 5. TÉLÉCHARGEMENT DIRECT
// ============================================================================

export async function triggerFileDownload(
  workdir: string,
  path: string,
  customFilename?: string,
  setError?: (err: string | null) => void,
  setLoading?: (loading: boolean) => void
): Promise<boolean> {
  try {
    if (setLoading) setLoading(true);
    if (setError) setError(null);

    const res = await downloadBackendFile(workdir, path, customFilename);
    if (!res.ok) {
      const errorMsg =
        typeof res.detail === "string"
          ? res.detail
          : res.detail?.message || res.error || "Échec du téléchargement du fichier.";
      if (setError) setError(errorMsg);
      return false;
    }

    return true;
  } catch (err: any) {
    const msg = logError(err);
    if (setError) setError(msg);
    return false;
  } finally {
    if (setLoading) setLoading(false);
  }
}