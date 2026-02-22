"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# ---------- Auth ----------


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"  # admin, operator, viewer


class RoleUpdateRequest(BaseModel):
    role: str  # admin, operator, viewer


# ---------- Tools ----------


class ToolInfo(BaseModel):
    name: str
    version: str
    category: str
    description: str
    capabilities: List[str] = []
    mitre_atlas: List[str] = []
    venv_path: str = ""
    cli_command: str = ""


class ToolRunRequest(BaseModel):
    target: str
    args: Dict[str, Any] = {}
    timeout: int = 600


class ToolRunResponse(BaseModel):
    tool: str
    target: str
    status: str
    output: str = ""
    duration_seconds: float = 0.0


# ---------- Attacks ----------


class AttackScenario(BaseModel):
    id: str
    name: str
    description: str
    severity: str = "medium"
    category: str = "general"
    tools: List[str]
    mitre_techniques: List[str] = []
    owasp_llm: List[str] = []
    arcanum_taxonomy: List[str] = []
    test_cases_count: int = 0
    prompt_count: int = 0
    multi_turn: bool = False
    config: Dict[str, Any] = {}


class AttackRunRequest(BaseModel):
    scenario_id: str
    target_model: str
    config: Dict[str, Any] = {}


class AttackRunResponse(BaseModel):
    id: str
    scenario_id: str
    target_model: str
    status: str
    progress: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    findings: List[Dict[str, Any]] = []


class AttackRunDetail(AttackRunResponse):
    config: Dict[str, Any] = {}
    results: Dict[str, Any] = {}
    error_message: Optional[str] = None
    findings: List[Dict[str, Any]] = []


# ---------- Findings ----------


class FindingSchema(BaseModel):
    id: str
    tool_name: str
    severity: str
    title: str
    description: Optional[str] = None
    mitre_technique: Optional[str] = None
    evidence: Dict[str, Any] = {}
    remediation: Optional[str] = None
    evidence_hash: Optional[str] = None
    created_at: datetime


# ---------- Reports ----------


class ReportRequest(BaseModel):
    run_id: str
    formats: List[str] = ["html"]
    template: str = "standard"  # "standard" or "executive"


class ReportResponse(BaseModel):
    id: str
    run_id: str
    format: str
    file_path: Optional[str] = None
    s3_key: Optional[str] = None
    generated_at: datetime


# ---------- Probes ----------


class ProbeInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: str = "1.0.0"
    is_active: bool = True


class ProbeRunRequest(BaseModel):
    probe_name: str
    target_model: str
    config: Dict[str, Any] = {}


# ---------- Playbooks ----------


class PlaybookInfo(BaseModel):
    id: str
    name: str
    description: str
    trigger: str
    severity: str
    steps: List[Dict[str, Any]] = []


class PlaybookRunRequest(BaseModel):
    playbook_id: str
    context: Dict[str, Any] = {}


# ---------- Health ----------


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    services: Dict[str, str] = {}
    timestamp: datetime


# ---------- Agent Testing ----------


class AgentTestRequest(BaseModel):
    endpoint: str
    allowed_tools: List[str] = []
    forbidden_actions: List[str] = []
    test_scenarios: List[str] = ["tool_misuse", "hallucination", "unauthorized_access"]


class AgentTestResponse(BaseModel):
    id: str
    endpoint: str
    status: str
    risk_level: str = "unknown"
    findings_count: int = 0
    results: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None


# ---------- Drift ----------


class DriftBaselineRequest(BaseModel):
    model: str
    test_suite: str = "default"
    provider: Optional[str] = None  # e.g. "openai", "anthropic", "bedrock"


class DriftCompareRequest(BaseModel):
    model: str
    baseline_id: str
    provider: Optional[str] = None


# ---------- Synthetic Data ----------


class SyntheticGenRequest(BaseModel):
    seed_prompts: List[str] = []
    mutations: List[str] = ["encoding", "translation", "synonym"]
    count: int = 100


class SyntheticGenResponse(BaseModel):
    id: str
    status: str
    total_generated: int = 0
    mutations_applied: List[str] = []
    samples: List[Dict[str, Any]] = []  # first 10 samples
    created_at: datetime


# ---------- Multi-Turn ----------


class MultiTurnResult(BaseModel):
    strategy: str
    model: str
    turn_count: int = 0
    escalation_detected: bool = False
    turns: List[Dict[str, Any]] = []  # [{role, content, safety_score}]


# ---------- Supply Chain ----------


class SupplyChainScanRequest(BaseModel):
    model_source: str  # e.g. "huggingface:gpt2"
    checks: List[str] = ["dependencies", "model_card", "license", "data_provenance"]


# ---------- Webhooks ----------

VALID_WEBHOOK_EVENTS = {
    "attack.completed",
    "attack.failed",
    "scan.completed",
    "report.generated",
    "agent.test.completed",
}


class WebhookCreateRequest(BaseModel):
    url: str
    events: List[str] = ["attack.completed"]
    description: Optional[str] = None


class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    is_active: bool
    description: Optional[str] = None
    failure_count: int = 0
    last_triggered_at: Optional[datetime] = None
    created_at: datetime


class WebhookCreatedResponse(WebhookResponse):
    secret: str  # Only returned on creation


class WebhookTestResponse(BaseModel):
    webhook_id: str
    status: str
    response_code: Optional[int] = None
    error: Optional[str] = None


# ---------- Scheduled Scans ----------


class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str  # e.g. "0 2 * * *" (nightly at 2am)
    scenario_id: str
    target_model: str
    config: Dict[str, Any] = {}
    compare_drift: bool = False
    baseline_id: Optional[str] = None


class ScheduleUpdateRequest(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    scenario_id: Optional[str] = None
    target_model: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    compare_drift: Optional[bool] = None
    baseline_id: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: str
    name: str
    cron_expression: str
    scenario_id: str
    target_model: str
    config: Dict[str, Any] = {}
    is_active: bool
    compare_drift: bool = False
    baseline_id: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---------- API Keys ----------


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = ["read", "write"]
    expires_in_days: Optional[int] = None  # None = never expires


class ApiKeyResponse(BaseModel):
    id: str
    prefix: str
    name: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str  # Only returned once on creation


# ---------- Notification Channels ----------

VALID_CHANNEL_TYPES = {"webhook", "slack", "email", "teams"}


class NotificationChannelCreate(BaseModel):
    channel_type: str  # webhook, slack, email, teams
    name: str
    config: Dict[str, Any] = {}  # URL, SMTP settings, etc.
    events: List[str] = ["attack.completed"]


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class NotificationChannelResponse(BaseModel):
    id: str
    channel_type: str
    name: str
    config: Dict[str, Any] = {}
    events: List[str]
    is_active: bool
    failure_count: int = 0
    last_triggered_at: Optional[datetime] = None
    created_at: datetime


class NotificationTestResponse(BaseModel):
    channel_id: str
    status: str
    error: Optional[str] = None


# ---------- Model Comparison ----------


class ComparisonRequest(BaseModel):
    scenario_id: str
    target_models: List[str]  # 2-5 models
    config: Dict[str, Any] = {}


class ComparisonResponse(BaseModel):
    id: str
    scenario_id: str
    target_models: List[str]
    run_ids: List[str]
    status: str
    created_at: datetime


# ---------- Batch Audit ----------


class AuditRequest(BaseModel):
    target_model: str
    config: Dict[str, Any] = {}
    scenario_ids: Optional[List[str]] = None  # None = all scenarios


class AuditResponse(BaseModel):
    id: str
    target_model: str
    scenario_count: int
    run_ids: List[str]
    status: str
    created_at: datetime


# ---------- Scoring Rubrics ----------


class ScoringRubricRequest(BaseModel):
    name: str
    rules: Dict[str, Any] = {}
    is_default: bool = False


class ScoringRubricResponse(BaseModel):
    id: str
    name: str
    rules: Dict[str, Any]
    is_default: bool
    created_at: datetime


# ---------- RAG Evaluation ----------


class RagDocument(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}  # {source, title, ...}


class RagEvalRequest(BaseModel):
    target_model: str
    documents: List[RagDocument] = []  # Empty = use built-in test corpus
    poison_documents: List[RagDocument] = []  # Empty = use built-in poisons
    queries: List[str] = []  # Empty = use built-in queries
    config: Dict[str, Any] = {}  # {top_k: 3, system_prompt: str?}


class RagEvalResponse(BaseModel):
    id: str
    target_model: str
    status: str
    run_type: str = "rag_eval"
    progress: float = 0.0
    created_at: datetime


class RagEvalDetail(RagEvalResponse):
    results: Dict[str, Any] = {}
    # results shape: {queries: [{query, retrieved_docs, has_poison, response, score}],
    #   summary: {total, poison_detected, context_leaked, avg_score}}
    findings: List[Dict[str, Any]] = []
    completed_at: Optional[datetime] = None


# ---------- Tool-Use Evaluation ----------


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = {}  # JSON Schema format


class ToolEvalPrompt(BaseModel):
    prompt: str
    expected_tool: Optional[str] = None
    forbidden: bool = False


class ToolEvalRequest(BaseModel):
    target_model: str
    tools: List[ToolDefinition] = []  # Empty = use built-in mock tools
    forbidden_tools: List[str] = []  # Empty = use defaults
    test_prompts: List[ToolEvalPrompt] = []  # Empty = use built-in prompts
    config: Dict[str, Any] = {}  # {max_iterations: 1, system_prompt: str?}


class ToolEvalResponse(BaseModel):
    id: str
    target_model: str
    status: str
    run_type: str = "tool_eval"
    progress: float = 0.0
    created_at: datetime


class ToolEvalDetail(ToolEvalResponse):
    results: Dict[str, Any] = {}
    # results shape: {prompts: [{prompt, tool_calls, mock_results, score, violations}],
    #   summary: {total, forbidden_blocked, hallucinations, arg_injections, avg_score}}
    findings: List[Dict[str, Any]] = []
    completed_at: Optional[datetime] = None


# ---------- Multimodal Evaluation ----------


class TestImageConfig(BaseModel):
    type: str  # text_overlay | metadata_injection | ocr_injection | custom
    text: str  # adversarial text to embed
    image_base64: Optional[str] = None  # for custom type


class MultimodalEvalRequest(BaseModel):
    target_model: str
    test_images: List[TestImageConfig] = []  # Empty = use built-in templates
    queries: List[str] = []  # Empty = use defaults
    config: Dict[str, Any] = {}  # {system_prompt: str?}


class MultimodalEvalResponse(BaseModel):
    id: str
    target_model: str
    status: str
    run_type: str = "multimodal_eval"
    progress: float = 0.0
    created_at: datetime


class MultimodalEvalDetail(MultimodalEvalResponse):
    results: Dict[str, Any] = {}
    # results shape: {images: [{type, embedded_text, query, response, score, image_preview}],
    #   summary: {total, injection_successes, avg_score}}
    findings: List[Dict[str, Any]] = []
    completed_at: Optional[datetime] = None


# ---------- Scoring Calibration ----------


class CalibrationRequest(BaseModel):
    target_model: str
    config: Dict[str, Any] = {}
    # config shape: {safe_prompt_count: 50, unsafe_prompt_count: 50,
    #   custom_safe_prompts: [str]?, custom_unsafe_prompts: [str]?}


class CalibrationResponse(BaseModel):
    id: str
    target_model: str
    status: str
    progress: float = 0.0
    created_at: datetime


class CalibrationDetail(CalibrationResponse):
    metrics: Dict[str, float] = {}
    # {precision, recall, f1, accuracy, auc}
    confusion_matrix: Dict[str, int] = {}
    # {tp, fp, tn, fn}
    roc_curve: List[Dict[str, float]] = []
    # [{threshold, tpr, fpr}]
    recommended_threshold: Optional[float] = None
    per_indicator_stats: List[Dict[str, Any]] = []
    # [{indicator, true_positives, false_positives, effectiveness}]
    completed_at: Optional[datetime] = None
