"""
Banking Customer Support Handlers
Each handler is a specialized "agent" for a specific message type.
"""

from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from db.db_utils import TicketManager

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()
client = OpenAI(api_key=os.getenv("PAID_OPENAI_API_KEY"))

# ============================================================================
# POSITIVE FEEDBACK AGENT
# ============================================================================

class PositiveFeedbackAgent:
    """
    Agent that handles positive feedback messages.
    Simply thanks the customer for their positive experience.
    """

    @staticmethod
    def handle(state: dict) -> dict:
        """
        Process positive feedback.

        :param state: Current workflow state
        :return: Dictionary with response updates
        """
        print("😊 [PositiveFeedbackAgent] Processing positive feedback...")

        customer_name = state["customer_name"]
        extracted_topic = state["extracted_topic"]
        user_input = state["user_input"]

        # Use OpenAI to generate a personalized thank you response
        system_prompt = """You are a friendly banking customer support agent responding to positive feedback.
        Generate a warm, professional, and appreciative response that:
        - Thanks the customer by name
        - Acknowledges their specific feedback
        - Expresses genuine appreciation
        - Keeps the tone professional but friendly
        - Keeps the response concise (2-3 sentences)"""

        user_prompt = f"""Customer name: {customer_name}
Topic they mentioned: {extracted_topic}
Their message: {user_input}

Generate a thank you response."""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )

            response = completion.choices[0].message.content.strip()
            print(f"✅ [PositiveFeedbackAgent] AI-generated response created!")

        except Exception as e:
            print(f"❌ [PositiveFeedbackAgent] OpenAI call failed: {str(e)}")
            response = "I'm sorry, but I'm currently unable to process your feedback. Please try again later."

        return {
            "response": response,
            "agent_name": "PositiveFeedbackAgent"
        }

# ============================================================================
# NEGATIVE FEEDBACK AGENT
# ============================================================================

class NegativeFeedbackAgent:
    """
    Agent that handles complaints and negative feedback.
    Creates a support ticket and reassures the customer.
    """

    @staticmethod
    def handle(state: dict) -> dict:
        """
        Process negative feedback and create a support ticket.

        :param state: Current workflow state
        :return: Dictionary with response and ticket info
        """
        print("😔 [NegativeFeedbackAgent] Processing complaint...")

        customer_id = state["customer_id"]
        customer_name = state["customer_name"]
        user_input = state["user_input"]
        extracted_topic = state["extracted_topic"]

        # TODO: Integrate database ticket creation
        from db.db_utils import TicketManager
        ticket_id = TicketManager.create_ticket(
            customer_id=customer_id,
            customer_name=customer_name,
            message_content=user_input,
            classification="negative_feedback"
        )

        # print(f"✅ [NegativeFeedbackAgent] Ticket {ticket_id} created!")
        
        system_prompt = """You are a compassionate banking customer support agent responding to a customer's complaint.
        Generate a warm, empathetic, and reassuring response that:
        - Acknowledges the customer's feelings and specific issue
        - Apologizes for their negative experience
        - Informs them that a support ticket has been created to address their issue
        - Provides a ticket number for reference
        - Addresses the customer by name
        - Keeps the tone professional but empathetic
        - Keeps the response concise (3-4 sentences)"""

        user_prompt = f"""Customer name: {customer_name}
        Topic they mentioned: {extracted_topic}
        Their complaint: {user_input}
        Their ticket ID: {ticket_id}
        """

        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            response = completion.choices[0].message.content.strip()
            print(f"✅ [NegativeFeedbackAgent] AI-generated response created!")

        except Exception as e:
            response = "I'm sorry, but I'm currently unable to process your request. Please try again later."
            print(f"❌ [NegativeFeedbackAgent] OpenAI call failed: {str(e)}")

        return {
            "response": response,
            "agent_name": "NegativeFeedbackAgent",
            # "ticket_id": ticket_id  # Uncomment when state includes ticket_id
        }


# ============================================================================
# QUERY AGENT
# ============================================================================

class QueryAgent:
    """
    Agent that handles ticket status queries.
    Looks up ticket information and provides status updates.
    """

    def __init__(self):
        self.get_ticket_status = TicketManager.get_ticket_status  # Bind the tool method to the agent instance

    @staticmethod
    def handle(state: dict) -> dict:
        """
        Process ticket query and look up status.

        :param state: Current workflow state
        :return: Dictionary with response and ticket status
        """
        print("🔍 [QueryAgent] Processing ticket query...")

        customer_id = state["customer_id"]
        customer_name = state["customer_name"]
        user_input = state["user_input"]
        extracted_topic = state["extracted_topic"]

        # TODO: Extract ticket number from user message
        # For now, we'll use a simple extraction
        ticket_number = QueryAgent._extract_ticket_number(user_input)

        if ticket_number:
            # TODO: Look up ticket in database
            from db.db_utils import TicketManager
            ticket = TicketManager.get_ticket(ticket_id=ticket_number)



            # Placeholder ticket lookup
            response = (
                f"Hello {customer_name}, I found ticket #{ticket_number}. "
                f"Status: In Progress. Our team is actively working on your issue regarding '{extracted_topic}'. "
                f"Expected resolution time: 24-48 hours."
            )
        else:
            # No ticket number found in message
            response = (
                f"Hello {customer_name}, I'd be happy to help you check your ticket status. "
                f"Could you please provide your ticket number? It should be a 6-digit number "
                f"that was sent to you when your issue was first reported."
            )

        print(f"✅ [QueryAgent] Response created!")

        return {
            "response": response,
            "agent_name": "QueryAgent"
        }

    @staticmethod
    def _extract_ticket_number(message: str) -> str:
        """
        Extract ticket number from user message.

        :param message: User's input message
        :return: Ticket number if found, empty string otherwise
        """
        import re

        # Look for patterns like "123456" or "#123456" or "ticket 123456"
        pattern = r'#?(\d{6})'
        match = re.search(pattern, message)

        if match:
            return match.group(1)

        return ""


# ============================================================================
# HANDLER ROUTER (for easy workflow integration)
# ============================================================================

def get_handler(classification_type: str):
    """
    Get the appropriate handler agent based on classification.

    :param classification_type: The classified message type
    :return: The handler function
    """
    handlers = {
        "positive_feedback": PositiveFeedbackAgent.handle,
        "negative_feedback": NegativeFeedbackAgent.handle,
        "query": QueryAgent.handle
    }

    return handlers.get(classification_type, QueryAgent.handle)
