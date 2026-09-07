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
} from "@/types/types";

import {
  getConfigRoute,
  setConfigRoute,
  getCatalogRoute,
  getSpecInfoRoute,
  createJobRoute,
  createAdvancedJobRoute,
  getJobStatusRoute,
  stopJobRoute,
  downloadFileRoute,
  checkBinaryRoute,
  statusRoute,
} from "./backend_routes";

import {
  _FetchResult,
  _fetch_get,
  _fetch_post,
  _fetch_blob,
  _DownloadResult,
} from "./fetch_functions_bases";
import { getConfig } from "./get_config";

/** Normalise la construction de l'URL pour éviter les doublons de slashs */
const buildUrl = (baseUrl: string, endpoint: string): string => {
  const cleanBase = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint.slice(1) : endpoint;
  return `${cleanBase}/${cleanEndpoint}`;
};

// ============================================================================
// 1. CONFIGURATION SERVEUR
// ============================================================================

export const getBackendConfig = async (token: string = ""): Promise<_FetchResult<WbConfig>> => {
  const conf = await getConfig();
  return await _fetch_get<WbConfig>(buildUrl(conf.apiBaseUrl, getConfigRoute), null, token);
};

export const setBackendConfig = async (
  data: UpdateConfigData | WbConfig,
  token: string = ""
): Promise<_FetchResult<{ success: boolean }>> => {
  const conf = await getConfig();
  return await _fetch_post<{ success: boolean }>(
    buildUrl(conf.apiBaseUrl, setConfigRoute),
    data,
    token,
    false
  );
};

// ============================================================================
// 2. CATALOGUE ET INTROSPECTION
// ============================================================================

export const getBackendCatalog = async (token: string = ""): Promise<_FetchResult<FullCatalogResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<FullCatalogResponse>(buildUrl(conf.apiBaseUrl, getCatalogRoute), null, token);
};

export const getBackendSpecInfo = async (
  specId: string,
  token: string = ""
): Promise<_FetchResult<SpecInfoResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<SpecInfoResponse>(
    buildUrl(conf.apiBaseUrl, getSpecInfoRoute(specId)),
    null,
    token
  );
};

// ============================================================================
// 3. LANCEMENT ET PILOTAGE DES JOBS
// ============================================================================

/**
 * Lance un job de catalogue standard avec téléversement multipart
 * (les fichiers sont ajoutés sous la même clé "files" comme attendu par FastAPI).
 */
export const createBackendJob = async (
  specId: string,
  userInput: Record<string, any>,
  files: (File | Blob)[] = [],
  timeout: number | null = null,
  token: string = ""
): Promise<_FetchResult<CreateJobResponse>> => {
  const conf = await getConfig();
  const formData = new FormData();

  formData.append(
    "data",
    JSON.stringify({
      id: specId,
      user_input: userInput,
      timeout: timeout ?? conf.defaultTimeout ?? 300,
    })
  );

  files.forEach((file) => {
    if (file instanceof File) {
      formData.append("files", file, file.name);
    } else {
      formData.append("files", file, "upload.bin");
    }
  });

  return await _fetch_post<CreateJobResponse>(
    buildUrl(conf.apiBaseUrl, createJobRoute),
    formData,
    token,
    true
  );
};

/**
 * Lance un job avancé / personnalisé (RawEntry)
 */
export const createAdvancedBackendJob = async (
  rawEntry: RawEntry | Record<string, any>,
  files: (File | Blob)[] = [],
  token: string = ""
): Promise<_FetchResult<CreateJobResponse>> => {
  const conf = await getConfig();
  const formData = new FormData();

  formData.append("data", JSON.stringify(rawEntry));

  files.forEach((file) => {
    if (file instanceof File) {
      formData.append("files", file, file.name);
    } else {
      formData.append("files", file, "upload.bin");
    }
  });

  return await _fetch_post<CreateJobResponse>(
    buildUrl(conf.apiBaseUrl, createAdvancedJobRoute),
    formData,
    token,
    true
  );
};

export const getBackendJobStatus = async (
  jobId: string,
  token: string = ""
): Promise<_FetchResult<JobStatusResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<JobStatusResponse>(
    buildUrl(conf.apiBaseUrl, getJobStatusRoute),
    `job_id=${encodeURIComponent(jobId)}`,
    token
  );
};

export const stopBackendJob = async (
  jobId: string,
  token: string = ""
): Promise<_FetchResult<JobStopResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<JobStopResponse>(
    buildUrl(conf.apiBaseUrl, stopJobRoute),
    `job_id=${encodeURIComponent(jobId)}`,
    token
  );
};

// ============================================================================
// 4. SANTÉ DU SYSTÈME & VÉRIFICATION DES BINAIRES
// ============================================================================

export const checkBackendBinary = async (
  toolName: ToolName | string,
  token: string = ""
): Promise<_FetchResult<BinaryCheckResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<BinaryCheckResponse>(
    buildUrl(conf.apiBaseUrl, checkBinaryRoute(toolName)),
    null,
    token
  );
};

export const getBackendStatus = async (token: string = ""): Promise<_FetchResult<ApiStatusResponse>> => {
  const conf = await getConfig();
  return await _fetch_get<ApiStatusResponse>(buildUrl(conf.apiBaseUrl, statusRoute), null, token);
};

// ============================================================================
// 5. TÉLÉCHARGEMENT DE FICHIERS
// ============================================================================

export const downloadBackendFile = async (
  workdir: string,
  path: string,
  customFilename?: string,
  token: string = ""
): Promise<_DownloadResult> => {
  const conf = await getConfig();
  const query = `workdir=${encodeURIComponent(workdir)}&path=${encodeURIComponent(path)}`;
  const fallback = customFilename || path.split("/").pop() || "downloaded_file";
  return await _fetch_blob(buildUrl(conf.apiBaseUrl, downloadFileRoute), query, fallback, token);
};

export const getDownloadFileUrl = async (workdir: string, path: string): Promise<string> => {
  const conf = await getConfig();
  const query = `workdir=${encodeURIComponent(workdir)}&path=${encodeURIComponent(path)}`;
  return `${buildUrl(conf.apiBaseUrl, downloadFileRoute)}?${query}`;
};