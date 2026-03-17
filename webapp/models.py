from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(String, primary_key=True, default=_uuid)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="idle")
    username = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    totals = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    duration_sec = Column(Float, nullable=True)
    settings_snapshot = Column(JSON, nullable=True)

    actions = relationship("JobAction", back_populates="job", cascade="all, delete-orphan")
    steps = relationship("JobStep", back_populates="job", cascade="all, delete-orphan")
    errors = relationship("JobError", back_populates="job", cascade="all, delete-orphan")
    artifacts = relationship("JobArtifact", back_populates="job", cascade="all, delete-orphan")
    browser_logs = relationship("BrowserLog", back_populates="job", cascade="all, delete-orphan")


class JobAction(Base):
    __tablename__ = "job_actions"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("job_runs.id"), index=True, nullable=True)
    action_type = Column(String, nullable=False)
    actor = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip = Column(String, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    job = relationship("JobRun", back_populates="actions")


class JobStep(Base):
    __tablename__ = "job_steps"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("job_runs.id"), index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="running")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    job = relationship("JobRun", back_populates="steps")


class JobError(Base):
    __tablename__ = "job_errors"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("job_runs.id"), index=True)
    message = Column(Text, nullable=False)
    stack = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    context = Column(JSON, nullable=True)

    job = relationship("JobRun", back_populates="errors")


class JobArtifact(Base):
    __tablename__ = "job_artifacts"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("job_runs.id"), index=True)
    type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobRun", back_populates="artifacts")


class BrowserLog(Base):
    __tablename__ = "browser_logs"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("job_runs.id"), index=True)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String, nullable=False)

    job = relationship("JobRun", back_populates="browser_logs")
