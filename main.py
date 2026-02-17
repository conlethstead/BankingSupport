from db.database import get_session, SupportTicket, InteractionLog, SessionHistory
from db.db_utils import TicketManager, LogManager, SessionManager

if __name__ == "__main__":
    print("Banking Customer Support AI - Agent Test")
    print("=" * 60)

    # Example usage of the database and utilities
    customer_id = "cust123"
    customer_name = "John Doe"
    message_content = "I need help with my account balance."
    classification = "query"

    # Create a support ticket
    ticket_id = TicketManager.create_ticket(customer_id, customer_name, message_content, classification)
    print(f"Created ticket with ID: {ticket_id}")

    # Log an interaction
    LogManager.log_interaction(
        customer_id=customer_id,
        input_message=message_content,
        classification=classification,
        confidence=0.95,
        extracted_topic="account_balance",
        ticket_id=ticket_id,
        agent_path="main.py",
        response="Sure, I can help you with that. Please provide your account number.",
        processing_time_ms=150
    )
    print("Logged interaction for the ticket.")

    # Retrieve and display the ticket
    ticket = TicketManager.get_ticket(ticket_id)
    print(f"Retrieved Ticket: {ticket}")