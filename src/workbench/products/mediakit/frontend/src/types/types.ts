// ============================================================================
// CONFIGURATION DE L'APPLICATION & DU SERVEUR
// ============================================================================

/** Configuration locale chargée depuis /config.json */
export interface AppConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  defaultTimeout?: number;
  productName: string;
  version: string;
}

/** Configuration globale MainEngine (WbConfig côté backend) */
export interface WbConfig {
  max_concurrent_job: number;
  buffer_max_lines: number | null;
  buffer_clear_delay: number;
  file_ttl: number;
}

/** Modèle de mise à jour partielle de la config */
export interface UpdateConfigData {
  max_concurrent_job?: number | null;
  buffer_max_lines?: number | null;
  buffer_clear_delay?: number | null;
  file_ttl?: number | null;
}

// ============================================================================
// INTROSPECTION DE SCHÉMA PYDANTIC (wb_utils/model_parser.py)
// ============================================================================

export interface FieldConstraint {
  ge?: number;
  le?: number;
  gt?: number;
  lt?: number;
  min_length?: number;
  max_length?: number;
}

export type FieldUiType =
  | "string"
  | "integer"
  | "float"
  | "boolean"
  | "enum"
  | "list[string]"
  | "list[any]"
  | string;

export interface ModelFieldMeta {
  name: string;
  type: FieldUiType;
  required: boolean;
  default: any;
  description: string;
  is_upload: boolean;
  choices: string[] | null;
  constraints: FieldConstraint;
  value?: any;
}

export type ModelSchema = Record<string, ModelFieldMeta>;

// ============================================================================
// CATALOGUE & DÉFINITIONS DES SPECS
// ============================================================================

export type ToolName = "ffmpeg" | "magick" | "sox";

export interface ActionSummary {
  id: string;
  label: string;
  type: "action";
  tool: ToolName;
  min_version?: [number, number, number?] | null;
}

export interface PipelineStepSummary {
  id: string;
  tool: ToolName;
  action_id: string;
  label?: string;
}

export interface PipelineSummary {
  id: string;
  label: string;
  type: "pipeline";
  steps: PipelineStepSummary[];
}

export type SpecSummary = ActionSummary | PipelineSummary;

export interface CategoryGroup<T = SpecSummary> {
  description: string;
  values: Record<string, T>;
}

export interface ToolCatalog<T = SpecSummary> {
  all_cat: Record<string, T>;
  categories: Record<string, CategoryGroup<T>>;
}

export interface FullCatalogResponse {
  action_specs: {
    ffmpeg: ToolCatalog<ActionSummary>;
    magick: ToolCatalog<ActionSummary>;
    sox: ToolCatalog<ActionSummary>;
    all_cat: Record<string, ActionSummary>;
  };
  pipeline_specs: {
    all_cat: Record<string, PipelineSummary>;
    categories?: Record<string, CategoryGroup<PipelineSummary>>;
  };
}

export interface SpecInfoResponse {
  success: boolean;
  input: ModelSchema;
  summary: SpecSummary;
  is_action_spec: boolean;
}

// ============================================================================
// SPECS AVANCÉES / PERSONNALISÉES (specs/raw_engine.py)
// ============================================================================

export type ArgTypeEnum = "path" | "int" | "float" | "bool" | "enum" | "pattern" | "multi_path";
export type MultiPathMode = "repeat_flag" | "positional" | "joined";

export interface RawArg {
  flag: string;
  value?: any;
  values?: any[] | null;
  min_value?: number | null;
  max_value?: number | null;
  must_exist?: boolean | null;
  type: ArgTypeEnum;
  mode?: MultiPathMode;
  separator?: string | null;
  is_upload_file?: boolean;
  enum_values?: string[] | null;
}

export interface RawEntry {
  tool: string;
  args: RawArg[];
  timeout?: number | null;
  capture_stdout?: boolean;
  output_filename: string;
  check_version?: boolean;
  min_version?: [number, number, number?] | null;
}

// ============================================================================
// CYCLE DE VIE, STATUT ET RÉSULTAT DES JOBS
// ============================================================================

export interface JobOutputFile {
  id: string;
  file: string | null;
  pos: number;
  last: boolean;
}

export interface CreateJobResponse {
  workdir: string;
  job_id: string;
  spec: SpecSummary;
  is_action_spec: boolean;
  is_custom_spec: boolean;
  output_files: JobOutputFile[];
}

export type JobStatusType = "running" | "stop" | "failed" | "finished" | "unknown";

export interface JobStatusResponse {
  status: JobStatusType;
}

export interface JobStopResponse {
  success: boolean;
}

export interface BinaryCheckResponse {
  find: boolean;
}

export interface ApiStatusResponse {
  status: string;
}

// ============================================================================
// ERREURS SYSTÈME (wb_utils/error_mapper.py)
// ============================================================================

export type ErrorCode =
  | "PIPELINE_STEP_FAILED"
  | "TOO_MANY_JOBS"
  | "INVALID_SPEC"
  | "JOB_ALREADY_EXISTS"
  | "JOB_TIMEOUT"
  | "JOB_CANCELLED"
  | "FORBIDDEN_PATH"
  | "FILE_NOT_FOUND"
  | "TOOL_MISSING"
  | "TOOL_UNVERIFIED"
  | "TOOL_VERSION_INCOMPATIBLE"
  | "VALIDATION_BUSINESS_ERROR"
  | "INVALID_INPUT_PARAMS"
  | "INVALID_ARGUMENT"
  | "INTERNAL_ENGINE_ERROR"
  | "UPLOAD_COUNT_MISMATCH"
  | "DUPLICATE_UPLOAD_NAME"
  | "INVALID_UPLOAD_NAME"
  | "NO_AUDIO_STREAM_FOUND"
  | "INVALID_DATA_FIELD";

export interface ApiErrorDetail {
  error_code?: ErrorCode;
  message?: string;
  status_code?: number;
  details?: Record<string, any>;
  [key: string]: any;
}

// ============================================================================
// MESSAGES DU WEBSOCKET (/job/ws/logs)
// ============================================================================

export type WsMessageType =
  | "replay_start"
  | "replay_end"
  | "run_log"
  | "job_result"
  | "job_end"
  | "info";

export interface WsBaseMessage {
  type: WsMessageType;
  timestamp?: string;
}

export interface WsReplayStartMessage extends WsBaseMessage {
  type: "replay_start";
  count: number;
  message: string;
}

export interface WsRunLogMessage extends WsBaseMessage {
  type: "run_log";
  stream: "stdout" | "stderr";
  text: string;
  step?: string;
}

export interface WsJobResultMessage extends WsBaseMessage {
  type: "job_result";
  result: {
    returncode?: number;
    ok?: boolean;
    success?: boolean;
    stdout?: string;
    stderr?: string;
    output_filename?: string;
    [key: string]: any;
  };
}

export interface WsInfoMessage extends WsBaseMessage {
  type: "info";
  message: string;
}

export type WsMessage =
  | WsReplayStartMessage
  | WsRunLogMessage
  | WsJobResultMessage
  | WsInfoMessage
  | WsBaseMessage;