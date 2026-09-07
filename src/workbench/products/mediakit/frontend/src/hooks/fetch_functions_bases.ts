import { logError } from "./error_utils";

export interface _FetchResult<T = Record<string, any>> {
  ok: boolean;
  response: T | null;
  error: string | null;
  status: number | null;
}

export interface _DownloadResult {
  ok: boolean;
  detail?: any;
  error?: string | null;
  status: number | null;
}

interface RequestHeaders {
  "Content-Type"?: string;
  Authorization?: string;
  [key: string]: string | undefined;
}

export const _fetch_post = async <T = Record<string, any>>(
  path: string,
  data: any,
  token: string = "",
  isFormData: boolean = false
): Promise<_FetchResult<T>> => {
  try {
    const headers: RequestHeaders = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    let body: BodyInit;
    if (isFormData) {
      body = data as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(data);
    }

    const res = await fetch(path, {
      method: "POST",
      body,
      headers: headers as Record<string, string>,
    });

    let jsonResponse: any = null;
    try {
      jsonResponse = await res.json();
    } catch {
      jsonResponse = null;
    }
    //alert(`${path} -> ${JSON.stringify(data)} -> ${JSON.stringify(jsonResponse)}`);
    return {
      ok: res.ok,
      response: jsonResponse,
      error: res.ok ? null : jsonResponse?.detail?.message || res.statusText,
      status: res.status,
    };
  } catch (err: any) {
    const msg = logError(err);
    console.error("Erreur _fetch_post :", msg);
    return {
      ok: false,
      response: null,
      error: msg || "Erreur de connexion réseau",
      status: null,
    };
  }
};

export const _fetch_get = async <T = Record<string, any>>(
  path: string,
  query: string | null = null,
  token: string = ""
): Promise<_FetchResult<T>> => {
  try {
    const headers: RequestHeaders = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    const url = query ? `${path}${path.includes("?") ? "&" : "?"}${query}` : path;
    const res = await fetch(url, {
      method: "GET",
      headers: headers as Record<string, string>,
    });

    let jsonResponse: any = null;
    try {
      jsonResponse = await res.json();
    } catch {
      jsonResponse = null;
    }
    //alert(`${path} -> ${query} -> ${JSON.stringify(jsonResponse)}`);
    return {
      ok: res.ok,
      response: jsonResponse,
      error: res.ok ? null : jsonResponse?.detail?.message || res.statusText,
      status: res.status,
    };
  } catch (err: any) {
    const msg = logError(err);
    console.error("Erreur _fetch_get :", msg);
    return {
      ok: false,
      response: null,
      error: msg || "Erreur de connexion réseau",
      status: null,
    };
  }
};

export const _fetch_blob = async (
  path: string,
  query: string | null = null,
  fallbackFilename: string = "downloaded_file",
  token: string = ""
): Promise<_DownloadResult> => {
  try {
    const headers: RequestHeaders = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    const url = query ? `${path}${path.includes("?") ? "&" : "?"}${query}` : path;
    const res = await fetch(url, {
      method: "GET",
      headers: headers as Record<string, string>,
    });

    if (!res.ok) {
      let detail: any = null;
      try {
        detail = await res.json();
      } catch {
        detail = await res.text();
      }
      return {
        ok: false,
        detail,
        error: `Erreur HTTP ${res.status}`,
        status: res.status,
      };
    }

    let filename = fallbackFilename;
    const disposition = res.headers.get("Content-Disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/);
      if (match && match[1]) {
        filename = decodeURIComponent(match[1].trim());
      }
    }

    const rawBlob = await res.blob();
    // Forçage en flux binaire pour bloquer l'ouverture directe dans le navigateur
    const downloadBlob = new Blob([rawBlob], { type: "application/octet-stream" });
    const downloadUrl = window.URL.createObjectURL(downloadBlob);

    const link = document.createElement("a");
    link.style.display = "none";
    link.href = downloadUrl;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();

    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    }, 150);

    return {
      ok: true,
      status: res.status,
    };
  } catch (err: any) {
    const msg = logError(err);
    console.error("Erreur _fetch_blob :", msg);
    return {
      ok: false,
      error: msg || "Échec du téléchargement réseau",
      status: null,
    };
  }
};