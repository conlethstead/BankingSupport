"""
Database utilities for Banking Customer Support AI
Common queries and operations
"""

from datetime import datetime, timedelta
from .database import get_session, SupportTicket, InteractionLog, SessionHistory
import random
from langchain.tools import tool


class TicketManager:
    """Manage support tickets"""

    @staticmethod
    def generate_ticket_id():
        """Generate a unique 6-digit ticket ID"""
        session = get_session()
        while True:
            ticket_id = str(random.randint(100000, 999999))
            existing = session.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
            if not existing:
                session.close()
                return ticket_id
        session.close()

    @staticmethod
    def create_ticket(customer_id, customer_name, message_content, classification):
        """Create a new support ticket"""
        session = get_session()
        ticket_id = TicketManager.generate_ticket_id()
        
        ticket = SupportTicket(
            ticket_id=ticket_id,
            customer_id=customer_id,
            customer_name=customer_name,
            message_content=message_content,
            classification=classification,
            status="unresolved"
        )
        
        session.add(ticket)
        session.commit()
        session.close()
        return ticket_id

    @staticmethod
    def get_ticket(ticket_id):
        """Retrieve a ticket by ID"""
        session = get_session()
        ticket = session.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
        session.close()
        return ticket

    @staticmethod
    def update_ticket_status(ticket_id, new_status):
        """Update ticket status"""
        session = get_session()
        ticket = session.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
        if ticket:
            ticket.status = new_status
            if new_status == "resolved":
                ticket.resolved_at = datetime.utcnow()
            ticket.last_updated = datetime.utcnow()
            session.commit()
        session.close()
        return ticket

    @staticmethod
    def add_agent_response(ticket_id, response):
        """Add agent response to ticket"""
        session = get_session()
        ticket = session.query(SupportTicket).filter_by(ticket_id=ticket_id).first()
        if ticket:
            ticket.agent_response = response
            ticket.last_updated = datetime.utcnow()
            session.commit()
        session.close()

    @staticmethod
    def list_tickets(status=None, customer_id=None, limit=10):
        """List tickets with optional filters"""
        session = get_session()
        query = session.query(SupportTicket)
        
        if status:
            query = query.filter_by(status=status)
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
        
        tickets = query.order_by(SupportTicket.created_at.desc()).limit(limit).all()
        session.close()
        return tickets
    
    @tool("Get ticket status")
    def get_ticket_status(ticket_id: str) -> str:
        """
        Tool to get the status of a support ticket by its ID.
        
        Args:
            ticket_id (str): The ID of the support ticket
            
        Returns:
            str: Status of the ticket or an error message if not found
        """
        print(f"🔍 [Tool] Fetching status for ticket ID: {ticket_id}")
        
        ticket = TicketManager.get_ticket(ticket_id)
        
        if ticket:
            print(f"✅ [Tool] Ticket found. Status: {ticket.status}")
            return f"Ticket #{ticket_id} is currently '{ticket.status}'."
        else:
            print(f"❌ [Tool] Ticket with ID {ticket_id} not found.")
            return f"Sorry, I couldn't find a ticket with ID {ticket_id}."


class LogManager:
    """Manage interaction logs"""

    @staticmethod
    def log_interaction(customer_id, input_message, classification, confidence,
                       extracted_topic, ticket_id, agent_path, response, processing_time_ms, errors=None):
        """Log a customer interaction"""
        session = get_session()
        
        log = InteractionLog(
            customer_id=customer_id,
            input_message=input_message,
            classification=classification,
            confidence=confidence,
            extracted_topic=extracted_topic,
            ticket_id=ticket_id,
            agent_path=agent_path,
            response=response,
            processing_time_ms=processing_time_ms,
            errors=str(errors) if errors else None
        )
        
        session.add(log)
        session.commit()
        log_id = log.log_id
        session.close()
        return log_id

    @staticmethod
    def get_logs_by_customer(customer_id, limit=20):
        """Get interaction logs for a customer"""
        session = get_session()
        logs = session.query(InteractionLog).filter_by(
            customer_id=customer_id
        ).order_by(InteractionLog.timestamp.desc()).limit(limit).all()
        session.close()
        return logs

    @staticmethod
    def get_logs_by_date_range(start_date, end_date):
        """Get logs within a date range"""
        session = get_session()
        logs = session.query(InteractionLog).filter(
            InteractionLog.timestamp >= start_date,
            InteractionLog.timestamp <= end_date
        ).order_by(InteractionLog.timestamp.desc()).all()
        session.close()
        return logs

    @staticmethod
    def get_stats(days=7):
        """Get interaction statistics for the last N days"""
        session = get_session()
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = session.query(InteractionLog).filter(
            InteractionLog.timestamp >= start_date
        ).all()
        
        stats = {
            "total_interactions": len(logs),
            "by_classification": {},
            "avg_confidence": 0,
            "avg_processing_time_ms": 0,
        }
        
        if logs:
            confidences = [log.confidence for log in logs if log.confidence]
            processing_times = [log.processing_time_ms for log in logs if log.processing_time_ms]
            
            stats["avg_confidence"] = sum(confidences) / len(confidences) if confidences else 0
            stats["avg_processing_time_ms"] = sum(processing_times) / len(processing_times) if processing_times else 0
            
            for log in logs:
                classification = log.classification or "unknown"
                stats["by_classification"][classification] = stats["by_classification"].get(classification, 0) + 1
        
        session.close()
        return stats


class SessionManager:
    """Manage session history"""

    @staticmethod
    def create_session(session_id, customer_id):
        """Create a new session"""
        session = get_session()
        hist = SessionHistory(
            session_id=session_id,
            customer_id=customer_id,
            interaction_logs_json="[]",
            session_context="{}"
        )
        session.add(hist)
        session.commit()
        session.close()

    @staticmethod
    def get_session_history(session_id):
        """Retrieve a session"""
        session = get_session()
        hist = session.query(SessionHistory).filter_by(session_id=session_id).first()
        session.close()
        return hist

    @staticmethod
    def update_session_context(session_id, context_dict):
        """Update session context"""
        import json
        session = get_session()
        hist = session.query(SessionHistory).filter_by(session_id=session_id).first()
        if hist:
            hist.session_context = json.dumps(context_dict)
            hist.last_accessed = datetime.utcnow()
            session.commit()
        session.close()


if __name__ == "__main__":
    # Example usage
    print("Testing database utilities...")
    
    # Generate ticket ID
    ticket_id = TicketManager.generate_ticket_id()
    print(f"Generated ticket ID: {ticket_id}")
    
    # Create a test ticket
    created_id = TicketManager.create_ticket(
        customer_id="TEST001",
        customer_name="Test Customer",
        message_content="Test message",
        classification="query"
    )
    print(f"Created ticket: {created_id}")
    
    # Get ticket
    ticket = TicketManager.get_ticket(created_id)
    print(f"Retrieved ticket: {ticket}")
    
    # Log interaction
    log_id = LogManager.log_interaction(
        customer_id="TEST001",
        input_message="Test message",
        classification="query",
        confidence=0.95,
        extracted_topic="general_inquiry",
        ticket_id=created_id,
        agent_path="query_handler",
        response="Here's the information...",
        processing_time_ms=450
    )
    print(f"Logged interaction: {log_id}")
    
    # Get stats
    stats = LogManager.get_stats(days=7)
    print(f"Stats (last 7 days): {stats}")
