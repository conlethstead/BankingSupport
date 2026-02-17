"""
Banking Customer Support AI - Database Setup and Management
Uses SQLite for simplicity and portability
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "banking_support.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine and base
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class SupportTicket(Base):
    """Support ticket model"""
    __tablename__ = "support_tickets"

    ticket_id = Column(String(10), primary_key=True)
    customer_id = Column(String(100), nullable=False, index=True)
    customer_name = Column(String(255))
    message_content = Column(Text, nullable=False)
    classification = Column(String(50))  # positive_feedback, negative_feedback, query
    status = Column(String(50), default="unresolved", index=True)  # unresolved, in_progress, resolved
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    agent_response = Column(Text)
    customer_feedback = Column(String(50), nullable=True)

    # Relationship to interaction logs
    interaction_logs = relationship("InteractionLog", back_populates="ticket")

    def __repr__(self):
        return f"<SupportTicket(ticket_id={self.ticket_id}, customer_id={self.customer_id}, status={self.status})>"


class InteractionLog(Base):
    """Interaction log model"""
    __tablename__ = "interaction_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(100), nullable=False, index=True)
    input_message = Column(Text, nullable=False)
    classification = Column(String(50))  # positive_feedback, negative_feedback, query
    confidence = Column(Float)  # 0.0-1.0
    extracted_topic = Column(String(255))
    ticket_id = Column(String(10), ForeignKey("support_tickets.ticket_id"), nullable=True)
    agent_path = Column(String(255))  # Which handler was used
    response = Column(Text)
    processing_time_ms = Column(Integer)  # Milliseconds
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    errors = Column(Text, nullable=True)  # JSON string of errors

    # Relationship to support ticket
    ticket = relationship("SupportTicket", back_populates="interaction_logs")

    def __repr__(self):
        return f"<InteractionLog(log_id={self.log_id}, customer_id={self.customer_id}, classification={self.classification})>"


class SessionHistory(Base):
    """Session history model"""
    __tablename__ = "session_history"

    session_id = Column(String(100), primary_key=True)
    customer_id = Column(String(100), index=True)
    interaction_logs_json = Column(Text)  # JSON string of log IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_context = Column(Text)  # JSON string of context

    def __repr__(self):
        return f"<SessionHistory(session_id={self.session_id}, customer_id={self.customer_id})>"


def init_db():
    """Initialize the database - create all tables"""
    Base.metadata.create_all(engine)
    print(f"✓ Database initialized at {DB_PATH}")
    return engine, SessionLocal


def get_session():
    """Get a database session"""
    return SessionLocal()


def seed_test_data():
    """Add sample test data to the database"""
    session = get_session()

    # Sample support tickets
    test_tickets = [
        SupportTicket(
            ticket_id="123456",
            customer_id="CUST001",
            customer_name="John Smith",
            message_content="My debit card replacement still hasn't arrived",
            classification="negative_feedback",
            status="unresolved",
            agent_response="We apologize for the inconvenience. A new ticket #123456 has been created to track your card replacement."
        ),
        SupportTicket(
            ticket_id="234567",
            customer_id="CUST002",
            customer_name="Sarah Johnson",
            message_content="Thanks for resolving my credit card issue quickly!",
            classification="positive_feedback",
            status="resolved",
            agent_response="Thank you for your kind feedback, Sarah! We're glad we could help resolve your credit card issue quickly.",
            customer_feedback="positive"
        ),
    ]

    for ticket in test_tickets:
        try:
            session.add(ticket)
        except Exception as e:
            print(f"Warning: Could not add ticket {ticket.ticket_id}: {e}")

    session.commit()
    print(f"✓ Added {len(test_tickets)} sample tickets")
    session.close()


if __name__ == "__main__":
    print("Initializing Banking Customer Support Database...")
    init_db()
    # Uncomment to seed test data:
    # seed_test_data()
