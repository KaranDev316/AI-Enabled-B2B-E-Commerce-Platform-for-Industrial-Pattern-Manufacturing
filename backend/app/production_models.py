from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ProductionJob(Base):
    __tablename__ = 'production_jobs'
    __table_args__ = (CheckConstraint('progress >= 0 AND progress <= 100', name='ck_job_progress'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='RESTRICT'), unique=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default='design_and_tooling', nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class JobStageHistory(Base):
    __tablename__ = 'job_stage_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('production_jobs.id', ondelete='RESTRICT'), index=True, nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    customer_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
