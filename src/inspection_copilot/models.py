"""Database schema (SQLAlchemy 2.0 typed ORM models).

Two halves:
  * Knowledge base: documents -> chunks. Each chunk stores its text, a vector embedding
    (pgvector) for semantic search and a tsvector for keyword search, so both retrieval
    methods run inside the same PostgreSQL database.
  * Inspection data: images -> detection_runs -> detections. A run is one model applied to
    one image (fast YOLOv8n or accurate YOLOv8s, as in the thesis), with its latency.
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from inspection_copilot.config import get_settings

EMBEDDING_DIM = get_settings().embedding_dim


class Base(DeclarativeBase):
    pass


# --- Knowledge base -------------------------------------------------------------------


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), unique=True)  # key in sources.toml
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    license: Mapped[str] = mapped_column(String(200))  # every document must state its licence
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer)  # position inside the document
    section: Mapped[str | None] = mapped_column(String(300))  # nearest heading, for citations
    # Page range the chunk covers (1-based). The evaluation labels relevant pages, which stay
    # valid when chunk size changes, unlike chunk ids.
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    # Generated column: PostgreSQL keeps it in sync with `text` automatically.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        # HNSW = approximate nearest-neighbour graph index; cosine distance matches how
        # sentence-embedding models are trained.
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # GIN = inverted index, the standard index for full-text search.
        Index("ix_chunks_tsv_gin", "tsv", postgresql_using="gin"),
    )


# --- Inspection data ------------------------------------------------------------------


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)  # avoids duplicate uploads
    insulator_type: Mapped[str] = mapped_column(String(50))  # glass | porcelain | composite
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list["DetectionRun"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )


class DetectionRun(Base):
    __tablename__ = "detection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(200))  # e.g. glass_y8n_fast
    mode: Mapped[str] = mapped_column(String(20))  # model that produced the boxes: fast | accurate
    requested_mode: Mapped[str] = mapped_column(String(20), server_default="fast")  # or auto
    escalated: Mapped[bool] = mapped_column(Boolean, server_default=false())  # auto: fast->accurate
    fast_ms: Mapped[float | None] = mapped_column(Float)  # auto: latency of the fast pass
    inference_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    image: Mapped[Image] = relationship(back_populates="runs")
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("detection_runs.id", ondelete="CASCADE"), index=True
    )
    class_name: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    # Bounding box in pixels (x1, y1) top-left, (x2, y2) bottom-right.
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)

    run: Mapped[DetectionRun] = relationship(back_populates="detections")
    reviews: Mapped[list["DetectionReview"]] = relationship(
        back_populates="detection", cascade="all, delete-orphan"
    )


class DetectionReview(Base):
    """Second opinion on one detection from a vision LLM (human-in-the-loop flagging)."""

    __tablename__ = "detection_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(
        ForeignKey("detections.id", ondelete="CASCADE"), index=True
    )
    model: Mapped[str] = mapped_column(String(100))
    agrees_with_detector: Mapped[bool] = mapped_column(Boolean)
    condition: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    needs_human_review: Mapped[bool] = mapped_column(Boolean)
    rationale: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    detection: Mapped[Detection] = relationship(back_populates="reviews")
