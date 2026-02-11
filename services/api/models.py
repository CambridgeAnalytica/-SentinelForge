"""
SQLAlchemy models for SentinelForge.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, DateTime, Float, Integer, Boolean, JSON, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID
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
    OPERATOR = "operator"
    VIEWER = "viewer"


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
    findings = relationship("Finding", back_populates="run", cascade="all, delete-orphan")
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

    results = relationship("DriftResult", back_populates="baseline", cascade="all, delete-orphan")


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
    scan_type = Column(String(100), default="behavioral")  # behavioral, pickle, weight_analysis
    results = Column(JSON, default=dict)
    indicators_found = Column(Integer, default=0)
    risk_level = Column(String(50), default="unknown")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


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
