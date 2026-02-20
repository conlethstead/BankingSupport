"""
Banking Customer Support Handlers
Each handler is a specialized "agent" for a specific message type.
"""

from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from db.db_utils import TicketManager

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()
client = OpenAI(api_key=os.getenv("PAID_OPENAI_API_KEY"))

# Max prior turns to include as context (each turn = user + assistant). Keeps prompts within token limits.
MAX_CONTEXT_TURNS = 5


def _messages_with_history(system_content: str, user_content: str, state: dict):
    """Build OpenAI messages list with optional conversation history for context."""
    history = state.get("conversation_history") or []
    if not isinstance(history, list):
        history = []
    # Take the most recent turns to avoid token overflow
    max_messages = MAX_CONTEXT_TURNS * 2  # user + assistant per turn
    history = history[-max_messages:] if len(history) > max_messages else history
    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_content})
    return messages


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
            messages = _messages_with_history(system_prompt, user_prompt, state)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
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

        ticket_id = TicketManager.create_ticket(
            customer_id=customer_id,
            customer_name=customer_name,
            message_content=user_input,
            classification="negative_feedback"
        )

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
                messages=_messages_with_history(system_prompt, user_prompt, state),
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
            "ticket_id": ticket_id
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
        # extracted_topic = state["extracted_topic"]

        ticket_number = QueryAgent._extract_ticket_number(user_input)
        ticket = TicketManager.get_ticket(ticket_id=ticket_number) if ticket_number else None
        out_ticket_id = ""
        out_ticket_status = ""

        system_prompt = """You are a friendly banking customer support agent responding to a ticket status query.
        - If you are given ticket information below: give a professional, concise status update using the status, dates, and issue. If multiple tickets are listed, summarize each briefly. For status 'in_progress', add that the team is working on it and typical resolution is within 24-48 hours if not already stated.
        - If no ticket information is given (e.g. no ticket found for customer ID or name): ask them to provide the 6-digit ticket number they received when the issue was reported.
        - If the customer provided a ticket number but no ticket was found: politely say that no ticket was found for that number and suggest they check the number or contact support.
        Use the customer's name. Keep the response to 2-4 sentences (or a bit more if summarizing multiple tickets)."""

        if ticket:
            created_str = ticket.created_at.strftime("%Y-%m-%d %H:%M") if ticket.created_at else "N/A"
            resolved_str = ticket.resolved_at.strftime("%Y-%m-%d %H:%M") if ticket.resolved_at else "N/A"
            ticket_context = (
                f"Ticket ID: {ticket.ticket_id}\n"
                f"Status: {ticket.status}\n"
                f"Created at: {created_str}\n"
                f"Resolved at: {resolved_str}\n"
                f"Issue: {ticket.message_content or 'N/A'}"
            )
            
            user_prompt = f"""Customer name: {customer_name}
                Customer ID: {customer_id}
                Their message: {user_input}
                Ticket found. Use this information for your response:
                {ticket_context}
                """
            out_ticket_id = ticket.ticket_id
            out_ticket_status = ticket.status

        elif ticket_number:
            ticket_context = f"The customer asked about ticket number {ticket_number}, but no ticket was found with that ID."
            user_prompt = f"""Customer name: {customer_name}
                Customer ID: {customer_id}
                Their message: {user_input}
                {ticket_context}
                """
            out_ticket_id = ticket_number
            out_ticket_status = "not_found"

        else:            # No ticket number: search by customer_id, then customer_name from state, then name extracted from message
            tickets = []
            if customer_id:
                tickets = TicketManager.list_tickets(customer_id=customer_id, limit=5)
            if not tickets and customer_name and customer_name.strip():
                tickets = TicketManager.list_tickets(customer_name=customer_name.strip(), limit=5)
            # If still no tickets (e.g. state has Guest), try extracting name from the message
            if not tickets:
                extracted_name = QueryAgent._extract_customer_name_from_message(user_input)
                if extracted_name:
                    tickets = TicketManager.list_tickets(customer_name=extracted_name, limit=5)
                # Common variant: "Charlie" -> "Charles" in case DB has full first name
                if not tickets and extracted_name and "Charlie" in extracted_name.split()[0]:
                    variant = extracted_name.replace("Charlie", "Charles", 1)
                    tickets = TicketManager.list_tickets(customer_name=variant, limit=5)

            if tickets:
                parts = []
                for t in tickets:
                    created_str = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "N/A"
                    resolved_str = t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "N/A"
                    parts.append(
                        f"Ticket ID: {t.ticket_id}\n"
                        f"Status: {t.status}\n"
                        f"Created at: {created_str}\n"
                        f"Resolved at: {resolved_str}\n"
                        f"Issue: {t.message_content or 'N/A'}"
                    )
                ticket_context = (
                    "Ticket(s) found for this customer. Use this information for your response:\n\n"
                    + "\n---\n\n".join(parts)
                )
                out_ticket_id = tickets[0].ticket_id
                out_ticket_status = tickets[0].status
                user_prompt = f"""Customer name: {customer_name}
                    Customer ID: {customer_id}
                    Their message: {user_input}
                    {ticket_context}
                    """
            else:
                ticket_context = (
                    "No ticket was found for this customer ID or name. "
                    "Please ask the customer to provide the 6-digit ticket number they received when the issue was reported."
                )
                user_prompt = f"""Customer name: {customer_name}
                    Customer ID: {customer_id}
                    Their message: {user_input}
                    {ticket_context}
                    """
                out_ticket_id = ""
                out_ticket_status = ""

        try:
            messages = _messages_with_history(system_prompt, user_prompt, state)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )

            response = completion.choices[0].message.content.strip()
            print(f"✅ [QueryAgent] AI-generated response created!")

        except Exception as e:
            response = "I'm sorry, but I'm currently unable to process your request. Please try again later."
            print(f"❌ [QueryAgent] OpenAI call failed: {str(e)}")

        result = {
            "response": response,
            "agent_name": "QueryAgent"
        }
        if out_ticket_id:
            result["ticket_id"] = out_ticket_id
        if out_ticket_status:
            result["ticket_status"] = out_ticket_status
        return result

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

    @staticmethod
    def _extract_customer_name_from_message(message: str) -> Optional[str]:
        """
        Extract a customer name from the message (e.g. "My name is Charlie Davis", "I'm Alice").
        Returns the name string or None if not found.
        """
        import re
        if not message or not message.strip():
            return None
        text = message.strip()
        # Case-insensitive patterns; capture name (letters, spaces, hyphens, apostrophes)
        patterns = [
            r"(?:my name is|i'm|i am|this is|call me|it's)\s+([A-Za-z][A-Za-z\s\-']*(?:\s+[A-Za-z][A-Za-z\s\-']*)*)",
            r"(?:name is|named)\s+([A-Za-z][A-Za-z\s\-']*(?:\s+[A-Za-z][A-Za-z\s\-']*)*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) >= 2 and len(name) <= 80:
                    return name
        return None

class ResponseAgent:
    """
    Agent that formats the response for the user.
    """

    @staticmethod
    def handle(state: dict) -> dict:
        """
        Format the response for the user.
        """
        print("🔍 [ResponseAgent] Formatting response...")

        response = state["response"]
        agent_name = state["agent_name"]

        system_prompt = """You are a friendly banking customer agent that formats a response for the user.
        You will receive a response from another agent. Your job is to format it as a single, clean message for the customer.

        Rules:
        - Output ONLY the message text. Do not wrap in JSON. Do not use a "response" key or any labels.
        - Use real line breaks between paragraphs.
        - Always end with: Best regards, Conleth Stead, Banking AI Agent
        """

        user_prompt = f"""Format this response from {agent_name} as a plain message for the customer (no JSON, no keys):

        {response}"""

        try:
            messages = _messages_with_history(system_prompt, user_prompt, state)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )

            response = completion.choices[0].message.content.strip()
            print(f"✅ [ResponseAgent] AI-generated response created!")

        except Exception as e:
            response = "I'm sorry, but I'm currently unable to process your request. Please try again later."
            print(f"❌ [ResponseAgent] OpenAI call failed: {str(e)}")

        # If the model still returned JSON, extract the message text
        if response.strip().startswith("{"):
            try:
                import json
                parsed = json.loads(response)
                if isinstance(parsed.get("response"), str):
                    response = parsed["response"]
            except (json.JSONDecodeError, TypeError):
                pass
        # Ensure literal \n in the string become real newlines for display
        # response = response.replace("\\n", "\n")
        return {"response": response}

class EscalationAgent:
    """
    Agent that escalates the interaction to a human agent.
    """

    @staticmethod
    def handle(state: dict) -> dict:
        """
        Escalate the interaction to a human agent.
        """
        print("🔍 [EscalationAgent] Escalating interaction to a human agent...")

        customer_name = state["customer_name"]
        user_input = state["user_input"]
        extracted_topic = state["extracted_topic"]

        system_prompt = """You are a friendly banking customer support agent escalating the interaction to a human agent.
        Generate a warm, professional, and reassuring response that:
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
            messages = _messages_with_history(system_prompt, user_prompt, state)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )

            response = completion.choices[0].message.content.strip()
            print(f"✅ [EscalationAgent] AI-generated response created!")

        except Exception as e:
            response = "I'm sorry, but I'm currently unable to process your request. Please try again later."
            print(f"❌ [EscalationAgent] OpenAI call failed: {str(e)}")

        return {"response": response, "agent_name": "EscalationAgent"}