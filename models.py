"""IndoFlow persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    plant: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    capacity_units: Mapped[int] = mapped_column(Integer, default=1)
    alloy_compatibility: Mapped[list[str]] = mapped_column(JSON, default=list)
    recipe_compatibility: Mapped[list[str]] = mapped_column(JSON, default=list)
    setup_changeover_mins: Mapped[int] = mapped_column(Integer, default=0)
    # Absolute planning-horizon blackout intervals in hours, e.g. [[8, 16]].
    # Weekly shift rules should be expanded to these windows for each horizon.
    blackout_windows: Mapped[list[list[float]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    sku_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    segment: Mapped[str] = mapped_column(String(32), index=True)
    alloy_family: Mapped[str] = mapped_column(String(48), index=True)
    sintering_recipe_id: Mapped[str] = mapped_column(String(64), index=True)
    cycle_times_mins: Mapped[dict[str, float]] = mapped_column(JSON)
    requires_machining: Mapped[bool] = mapped_column(Boolean, default=True)
    # NULL preserves the legacy default route for existing parts.
    process_route: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    tool_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (Index("ix_work_orders_status_due", "status", "due_date_hours"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    wo_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("parts.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    due_date_hours: Mapped[float] = mapped_column(Float)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    current_stage: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    wip_age_hours: Mapped[float] = mapped_column(Float, default=0)
    locked_resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    locked_until_hour: Mapped[float] = mapped_column(Float, default=0)


class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    mode: Mapped[str] = mapped_column(String(32), index=True)
    total_late_orders: Mapped[int] = mapped_column(Integer, default=0)
    avg_wip_age_hours: Mapped[float] = mapped_column(Float, default=0)
    bottleneck_resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id", ondelete="SET NULL"), nullable=True)
    summary_metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class ScheduledOperation(Base):
    __tablename__ = "scheduled_operations"
    __table_args__ = (
        Index("ix_scheduled_operations_version", "schedule_version_id"),
        Index("ix_scheduled_operations_work_order", "work_order_id"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=new_id)
    schedule_version_id: Mapped[str] = mapped_column(ForeignKey("schedule_versions.id", ondelete="CASCADE"), index=True)
    work_order_id: Mapped[str] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    start_hour: Mapped[float] = mapped_column(Float)
    end_hour: Mapped[float] = mapped_column(Float)
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    delay_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
