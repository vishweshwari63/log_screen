import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Boolean, Float, Text, ForeignKey, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class SentimentEnum(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    SKEPTICAL = "SKEPTICAL"
    NEGATIVE = "NEGATIVE"

class HCP(Base):
    __tablename__ = "hcp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    hospital: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    preferred_products: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # JSON list of products
    relationship_score: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)  # Score between 1.0 and 10.0
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    interactions: Mapped[List["Interaction"]] = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = "interaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hcp_id: Mapped[int] = mapped_column(Integer, ForeignKey("hcp.id", ondelete="CASCADE"), nullable=False)
    rep_id: Mapped[str] = mapped_column(String(100), nullable=False)  # ID of the Medical Representative
    interaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)  # "structured" or "chat"
    discussion_topics: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # JSON array
    products_discussed: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # JSON array
    samples_distributed: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # JSON array
    competitors_mentioned: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # JSON array
    objections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sentiment: Mapped[SentimentEnum] = mapped_column(SQLEnum(SentimentEnum), nullable=False)
    sentiment_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    hcp: Mapped["HCP"] = relationship("HCP", back_populates="interactions")
    follow_ups: Mapped[List["FollowUp"]] = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")
    agent_logs: Mapped[List["AgentRunLog"]] = relationship("AgentRunLog", back_populates="interaction", cascade="all, delete-orphan")

class FollowUp(Base):
    __tablename__ = "follow_up"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("interaction.id", ondelete="CASCADE"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, COMPLETED, CANCELLED
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    interaction: Mapped["Interaction"] = relationship("Interaction", back_populates="follow_ups")

class AgentRunLog(Base):
    __tablename__ = "agent_run_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("interaction.id", ondelete="SET NULL"), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # SUCCESS, FAILED
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    interaction: Mapped[Optional["Interaction"]] = relationship("Interaction", back_populates="agent_logs")
