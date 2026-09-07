import { useState, useEffect, useRef, useCallback } from "react";
import { getConfig } from "./get_config";
import { wsLogsRoute } from "./backend_routes";
import { WsInfoMessage, WsJobResultMessage, WsMessage, WsRunLogMessage } from "@/types/types";

export interface LogLine {
  id: string;
  stream: "stdout" | "stderr";
  text: string;
  timestamp?: string;
  step?: string;
}

export interface UseJobLogsOptions {
  autoConnect?: boolean;
  onResult?: (result: any) => void;
  onEnd?: () => void;
  onError?: (err: Event | string) => void;
}

const getWsBaseUrl = (configuredBase: string) => {
  if (configuredBase && (configuredBase.startsWith("ws://") || configuredBase.startsWith("wss://"))) {
    return configuredBase;
  }
  // Si vide ou relatif, on prend le domaine et le port actuels de la page
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api`;
};

export function useJobLogs(jobId: string | null, options: UseJobLogsOptions = {}) {
  const { autoConnect = true, onResult, onEnd, onError } = options;

  // 👈 CRITIQUE : Protéger les callbacks contre les boucles de re-render
  const onResultRef = useRef(onResult);
  const onEndRef = useRef(onEnd);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onResultRef.current = onResult;
    onEndRef.current = onEnd;
    onErrorRef.current = onError;
  }, []);

  const [logs, setLogs] = useState<LogLine[]>([]);
  const [status, setStatus] = useState<"idle" | "connecting" | "connected" | "finished" | "error">("idle");
  const [jobResult, setJobResult] = useState<any | null>(null);
  const [isReplaying, setIsReplaying] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const lineCounterRef = useRef(0);

  const clearLogs = useCallback(() => {
    setLogs([]);
    setJobResult(null);
  }, []);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close(1000, "Client disconnect");
      socketRef.current = null;
    }
    setStatus("idle");
  }, []);

  const connect = useCallback(async () => {
    if (!jobId) return;

    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    setStatus("connecting");

    try {
      const conf = await getConfig();
      const rawBase = (conf.wsBaseUrl || "").trim();
      const cleanBase = rawBase.endsWith("/") ? rawBase.slice(0, -1) : rawBase;
      const wsBase = getWsBaseUrl(cleanBase);
      const wsUrl = `${wsBase}/${wsLogsRoute(jobId)}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data: WsMessage = JSON.parse(event.data);

          switch (data.type) {
            case "replay_start":
              setIsReplaying(true);
              break;

            case "replay_end":
              setIsReplaying(false);
              break;

            case "run_log": {
              const runLog = data as WsRunLogMessage;
              lineCounterRef.current += 1;
              const newLine: LogLine = {
                id: `${jobId}-${lineCounterRef.current}`,
                stream: runLog.stream || "stdout",
                text: runLog.text || "",
                timestamp: runLog.timestamp,
                step: runLog.step,
              };
              setLogs((prev) => [...prev, newLine]);
              break;
            }

            case "job_result":
                let jobResult = data as WsJobResultMessage;
                setJobResult(jobResult.result);
                onResultRef.current?.(jobResult.result);
                break;

            case "job_end":
                setStatus("finished");
                onEndRef?.current();
                ws.close(1000, "Job completed normally");
                socketRef.current = null;
                break;

            case "info":
                let jobInfo = data as WsInfoMessage;
                if (jobInfo.message === "job_stop") {
                    setStatus("finished");
                }
                break;

            default:
              break;
          }
        } catch (parseErr) {
          console.error("Erreur parsing WebSocket :", parseErr);
        }
      };

      ws.onerror = (err) => {
        setStatus("error");
        if (onErrorRef.current) onErrorRef.current(err);
      };

      ws.onclose = () => {
        setStatus((prev) => (prev === "finished" ? "finished" : "idle"));
        socketRef.current = null;
      };
    } catch (err: any) {
      setStatus("error");
      if (onErrorRef.current) onErrorRef.current(String(err));
    }
  }, [jobId]); // 👈 Ne dépend PLUS des callbacks !

  useEffect(() => {
    if (jobId && autoConnect) {
      clearLogs();
      connect();
    }
    return () => {
      disconnect();
    };
  }, [jobId, autoConnect, connect, disconnect, clearLogs]);

  return {
    logs,
    status,
    jobResult,
    isReplaying,
    clearLogs,
    reconnect: connect,
    disconnect,
  };
}