import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    documents = relationship("Document", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(500), default="Untitled Document")
    original_text = Column(Text, nullable=False)
    status = Column(String(20), default="processing")
    progress = Column(Integer, default=0)
    total_clauses = Column(Integer, default=0)
    processed_clauses = Column(Integer, default=0)
    risk_summary = Column(JSON, default=dict)
    document_summary = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    clause_index = Column(Integer, nullable=False)
    original_text = Column(Text, nullable=False)
    suggested_text = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(10), default="low")
    cosine_component = Column(Float, default=0.0)
    keyword_component = Column(Float, default=0.0)
    category = Column(String(50), default="general")
    flags = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    pros = Column(JSON, default=list)
    cons = Column(JSON, default=list)
    quality = Column(JSON, default=dict)
    compliance_matches = Column(JSON, default=list)
    llm_analysis = Column(JSON, nullable=True)

    document = relationship("Document", back_populates="clauses")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="chat_messages")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
