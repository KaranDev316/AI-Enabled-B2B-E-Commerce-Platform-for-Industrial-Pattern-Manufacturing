"""Private Employee production issues; separate from customer support."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ProductionIssue(Base):
    __tablename__ = 'production_issues'
    __table_args__ = (
        CheckConstraint("issue_type IN ('production','machine','material','drawing')", name='ck_issue_type'),
        CheckConstraint("priority IN ('high','medium','low')", name='ck_issue_priority'),
        CheckConstraint("status IN ('open','in_review','in_progress','resolved')", name='ck_issue_status'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey('production_jobs.id', ondelete='RESTRICT'), nullable=True)
    issue_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default='open')
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProductionIssueFile(Base):
    __tablename__ = 'production_issue_files'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('production_issues.id', ondelete='RESTRICT'), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(50))
    file_size_bytes: Mapped[int] = mapped_column(Integer)

class ProductionIssueEvent(Base):
    __tablename__ = 'production_issue_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('production_issues.id', ondelete='RESTRICT'), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
