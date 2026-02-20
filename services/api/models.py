"""
SQLAlchemy models for SentinelForge.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Float,
    Integer,
    Boolean,
    JSON,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


# ---------- Enums ----------


class RunStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, PyEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    OPERATOR = "operator"  # Legacy — maps to analyst
    VIEWER = "viewer"  # Legacy — read-only


class ReportFormat(str, PyEnum):
    HTML = "html"
    PDF = "pdf"
    JSONL = "jsonl"


class Severity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------- Models ----------


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    runs = relationship("AttackRun", back_populates="user")


class AttackRun(Base):
    __tablename__ = "attack_runs"

    id = Column(String, primary_key=True, default=new_uuid)
    scenario_id = Column(String(100), nullable=False, index=True)
    target_model = Column(String(200), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    progress = Column(Float, default=0.0)
    config = Column(JSON, default=dict)
    results = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="runs")
    findings = relationship(
        "Finding", back_populates="run", cascade="all, delete-orphan"
    )
    reports = relationship("Report", back_populates="run", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=new_uuid)
    run_id = Column(String, ForeignKey("attack_runs.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    severity = Column(Enum(Severity), default=Severity.INFO, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    mitre_technique = Column(String(50), nullable=True)
    evidence = Column(JSON, default=dict)
    remediation = Column(Text, nullable=True)
    evidence_hash = Column(String(64), nullable=True)  # SHA-256 hex
    previous_hash = Column(String(64), nullable=True)  # Chain link to previous finding
    fingerprint = Column(String(64), nullable=True, index=True)  # Dedup fingerprint
    is_new = Column(Boolean, default=True)  # True if first occurrence of fingerprint
    false_positive = Column(Boolean, default=False)  # Analyst-marked false positive
    created_at = Column(DateTime(timezone=True), default=utcnow)

    run = relationship("AttackRun", back_populates="findings")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=new_uuid)
    run_id = Column(String, ForeignKey("attack_runs.id"), nullable=False)
    format = Column(Enum(ReportFormat), nullable=False)
    file_path = Column(String(500), nullable=True)
    s3_key = Column(String(500), nullable=True)
    generated_at = Column(DateTime(timezone=True), default=utcnow)

    run = relationship("AttackRun", back_populates="reports")


class ProbeModule(Base):
    __tablename__ = "probe_modules"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    version = Column(String(20), default="1.0.0")
    config_schema = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class DriftBaseline(Base):
    __tablename__ = "drift_baselines"

    id = Column(String, primary_key=True, default=new_uuid)
    model_name = Column(String(200), nullable=False, index=True)
    test_suite = Column(String(100), default="default")
    scores = Column(JSON, default=dict)  # {category: score} baseline snapshot
    prompt_count = Column(Integer, default=0)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    results = relationship(
        "DriftResult", back_populates="baseline", cascade="all, delete-orphan"
    )


class DriftResult(Base):
    __tablename__ = "drift_results"

    id = Column(String, primary_key=True, default=new_uuid)
    baseline_id = Column(String, ForeignKey("drift_baselines.id"), nullable=False)
    model_name = Column(String(200), nullable=False)
    scores = Column(JSON, default=dict)  # {category: score} current snapshot
    deltas = Column(JSON, default=dict)  # {category: delta} vs baseline
    drift_detected = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    baseline = relationship("DriftBaseline", back_populates="results")


class SupplyChainScan(Base):
    __tablename__ = "supply_chain_scans"

    id = Column(String, primary_key=True, default=new_uuid)
    model_source = Column(String(500), nullable=False)  # e.g. "huggingface:gpt2"
    checks_requested = Column(JSON, default=list)
    results = Column(JSON, default=dict)
    risk_level = Column(String(50), default="unknown")
    issues_found = Column(Integer, default=0)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class BackdoorScan(Base):
    __tablename__ = "backdoor_scans"

    id = Column(String, primary_key=True, default=new_uuid)
    model_source = Column(String(500), nullable=False)
    scan_type = Column(
        String(100), default="behavioral"
    )  # behavioral, pickle, weight_analysis
    results = Column(JSON, default=dict)
    indicators_found = Column(Integer, default=0)
    risk_level = Column(String(50), default="unknown")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AgentTest(Base):
    __tablename__ = "agent_tests"

    id = Column(String, primary_key=True, default=new_uuid)
    endpoint = Column(String(500), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    config = Column(
        JSON, default=dict
    )  # {allowed_tools, forbidden_actions, test_scenarios}
    results = Column(JSON, default=dict)  # per-scenario results
    risk_level = Column(String(50), default="unknown")
    findings_count = Column(Integer, default=0)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class SyntheticDataset(Base):
    __tablename__ = "synthetic_datasets"

    id = Column(String, primary_key=True, default=new_uuid)
    seed_count = Column(Integer, default=0)
    mutations_applied = Column(JSON, default=list)  # ["encoding", "synonym", ...]
    total_generated = Column(Integer, default=0)
    status = Column(Enum(RunStatus), default=RunStatus.QUEUED, nullable=False)
    results = Column(JSON, default=dict)  # {samples: [...], stats: {...}}
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    url = Column(String(2000), nullable=False)
    events = Column(JSON, default=list)  # ["attack.completed", "scan.completed", ...]
    secret = Column(String(255), nullable=False)  # HMAC-SHA256 signing secret
    is_active = Column(Boolean, default=True)
    description = Column(String(500), nullable=True)
    failure_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ---------- Scheduled Scans ----------


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String(200), nullable=False)
    cron_expression = Column(String(100), nullable=False)  # e.g. "0 2 * * *"
    scenario_id = Column(String(100), nullable=False)
    target_model = Column(String(200), nullable=False)
    config = Column(JSON, default=dict)  # Tool config, passed to attack run
    is_active = Column(Boolean, default=True)
    compare_drift = Column(Boolean, default=False)  # Auto-compare drift each run
    baseline_id = Column(
        String, ForeignKey("drift_baselines.id"), nullable=True
    )  # Drift baseline to compare against
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------- API Keys ----------


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    prefix = Column(String(12), nullable=False)  # "sf_xxxx" for display
    name = Column(String(200), nullable=False)
    scopes = Column(JSON, default=list)  # ["read", "write", "admin"]
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User")


# ---------- Notification Channels ----------


class ChannelType(str, PyEnum):
    WEBHOOK = "webhook"
    SLACK = "slack"
    EMAIL = "email"
    TEAMS = "teams"


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(String, primary_key=True, default=new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel_type = Column(Enum(ChannelType), nullable=False)
    name = Column(String(200), nullable=False)
    config = Column(JSON, default=dict)  # URL, SMTP settings, etc.
    events = Column(JSON, default=list)  # ["attack.completed", "scan.completed"]
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------- Compliance Mappings ----------


class ComplianceMapping(Base):
    __tablename__ = "compliance_mappings"

    id = Column(String, primary_key=True, default=new_uuid)
    framework_id = Column(String(100), nullable=False, index=True)
    category_id = Column(String(100), nullable=False)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    finding = relationship("Finding")
