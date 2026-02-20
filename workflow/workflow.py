from typing import TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import time
from pathlib import Path

# Add parent directory to Python path so we can import agents module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our specialized agents
from agents.handlers import NegativeFeedbackAgent, PositiveFeedbackAgent, QueryAgent, ResponseAgent, EscalationAgent
from db.db_utils import LogManager, SessionManager

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("PAID_OPENAI_API_KEY"))

# Route to escalation when classification confidence is below this (PRD: "uncertain")
CONFIDENCE_THRESHOLD = 0.75

class MessageClassification(BaseModel):
    """
    Docstring for MessageClassification
    """
    classified_type: Literal["query", "positive_feedback", "negative_feedback"]
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of the classification decision"
    )
    extracted_topic: str = Field(
        ...,
        description="The main topic extracted from the user's message"
    )


class _BankingAgentStateRequired(TypedDict):
    # Input
    user_input: str
    customer_id: str
    customer_name: str

    # Classification
    classified_type: str  # query, positive_feedback, negative_feedback
    classification_confidence: float
    extracted_topic: str

    # Ticket info
    ticket_id: str
    ticket_status: str

    # Agent Response
    response: str
    agent_name: str  # which agent handled the query


class _BankingAgentStateOptional(TypedDict, total=False):
    session_id: str  # Optional: links interaction to a UI session for session history
    conversation_history: list  # Optional: list of {"role": "user"|"assistant", "content": str} for LLM context
    processing_start_time: float  # Internal: set by validate_input for timing
    processing_time_ms: int  # Computed in log_interaction from start time


class BankingAgentState(_BankingAgentStateRequired, _BankingAgentStateOptional):
    pass
    

def validate_input(state):
    """Validate user input and capture processing start time."""
    print("📥 [validate_input] Running validation...")

    start_time = time.perf_counter()

    user_input = state.get("user_input", "").strip()
    customer_id = state.get("customer_id", "").strip()
    customer_name = state.get("customer_name", "").strip()

    if not user_input:
        raise ValueError("User input cannot be empty.")
    if not customer_id:
        raise ValueError("Customer ID cannot be empty.")
    if not customer_name:
        raise ValueError("Customer name cannot be empty.")

    print(f"✅ [validate_input] Validation passed!")
    print(f"   - Customer: {customer_name} ({customer_id})")
    print(f"   - Message: {user_input[:50]}...")

    return {
        "user_input": user_input,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "processing_start_time": start_time
    }

def classify_message(state: BankingAgentState) -> dict:
    """
    Classify customer message using LLM with structured JSON output.

    :param state: Current workflow state containing user_input
    :type state: BankingAgentState
    :return: Dictionary with classification results
    :rtype: dict
    """
    print("🔍 [classify_message] Classifying message...")

    user_input = state["user_input"]

    system_prompt = """You are a classification expert for a banking customer support system.
    Your task is to classify customer messages into three categories:

    1. **positive_feedback**: Messages that express satisfaction, praise, thanks, or positive sentiment.
       Example: "Thank you for your help, I'm very happy with the service!"

    2. **negative_feedback**: Messages that express dissatisfaction, complaints, frustration, or negative sentiment.
       Example: "I'm really upset with how my issue was handled, this is terrible service."

    3. **query**: Messages that contain a question, request for information, or any message that is not clearly positive or negative feedback.
       Example: "Can you tell me why my account was charged twice?"

    Analyze the message and provide your classification."""

    user_prompt = f'Classify this customer message: "{user_input}"'

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=MessageClassification,
            temperature=0.0
        )

        classification = response.choices[0].message.parsed

        print(f"✅ [classify_message] Classification successful!")
        print(f"   - Type: {classification.classified_type}")
        print(f"   - Confidence: {classification.confidence:.2f}")
        print(f"   - Topic: {classification.extracted_topic}")

        return {
            "classified_type": classification.classified_type,
            "classification_confidence": classification.confidence,
            "extracted_topic": classification.extracted_topic
        }
    except Exception as e:
        print(f"❌ [classify_message] Classification failed: {str(e)}")
        return {
            "classified_type": "query",
            "classification_confidence": 0.5,
            "extracted_topic": user_input[:50]
        }

# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_by_classification(state: BankingAgentState) -> str:
    """
    Router that picks the content handler by classification type only.
    """
    classified_type = state["classified_type"]
    if classified_type == "positive_feedback":
        return "positive_feedback_handler"
    elif classified_type == "negative_feedback":
        return "negative_feedback_handler"
    elif classified_type == "query":
        return "query_handler"
    else:
        raise ValueError(f"Invalid classification type: {classified_type}")


def route_after_classification(state: BankingAgentState) -> str:
    """
    Router from classify_message: low confidence → escalation, else → content handler.
    """
    confidence = state.get("classification_confidence", 0.0)
    classified_type = state["classified_type"]

    if confidence < CONFIDENCE_THRESHOLD:
        print(f"🔀 [router] Low confidence ({confidence:.2f}) → escalation_handler")
        return "escalation_handler"
    print(f"🔀 [router] Routing to: {classified_type}_handler")
    return route_by_classification(state)

# ============================================================================
# HANDLER NODES (delegate to specialized agents)
# ============================================================================

def positive_feedback_handler(state: BankingAgentState) -> dict:
    """
    Handler node for positive feedback - delegates to PositiveFeedbackAgent.
    """
    return PositiveFeedbackAgent.handle(state)
    
def negative_feedback_handler(state: BankingAgentState) -> dict:
    """
    Handler node for negative feedback - delegates to NegativeFeedbackAgent.
    """
    return NegativeFeedbackAgent.handle(state)

def query_handler(state: BankingAgentState) -> dict:
    """
    Handler node for queries - delegates to QueryAgent.
    """
    return QueryAgent.handle(state)

def format_response(state: BankingAgentState) -> dict:
    """
    Format the response for the user.
    """
    return ResponseAgent.handle(state)

def log_interaction(state: BankingAgentState) -> dict:
    """
    Log the interaction to the database. Extracts fields from state for LogManager.
    Computes processing_time_ms from processing_start_time if available.
    If session_id is present, appends the new log to that session via SessionManager.
    """
    start_time = state.get("processing_start_time")
    if start_time:
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)
    else:
        processing_time_ms = state.get("processing_time_ms", 0)

    log_id = LogManager.log_interaction(
        customer_id=state.get("customer_id", ""),
        input_message=state.get("user_input", ""),
        classification=state.get("classified_type", ""),
        confidence=state.get("classification_confidence"),
        extracted_topic=state.get("extracted_topic", ""),
        ticket_id=state.get("ticket_id") or None,
        agent_path=state.get("agent_name", ""),
        response=state.get("response", ""),
        processing_time_ms=processing_time_ms,
        errors=None,
    )
    session_id = state.get("session_id")
    if session_id and state.get("customer_id"):
        SessionManager.add_interaction_to_session(
            session_id, state["customer_id"], log_id
        )
    return {"processing_time_ms": processing_time_ms}

def escalation_handler(state: BankingAgentState) -> dict:
    """
    Escalate the interaction to a human agent.
    """
    return EscalationAgent.handle(state)


def build_workflow():
    """
    Build and compile the banking support workflow with conditional routing.

    Flow:
    START -> validate_input -> classify_message -> [ROUTER] -> positive_feedback_handler -> END

    Note: Only positive and negative feedback handlers are implemented for now.
    """
    print("\n🔧 Building workflow (positive and negative feedback handlers)...")

    workflow = StateGraph(BankingAgentState)

    # Add nodes
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("classify_message", classify_message)
    workflow.add_node("escalation_handler", escalation_handler)
    workflow.add_node("positive_feedback_handler", positive_feedback_handler)
    workflow.add_node("negative_feedback_handler", negative_feedback_handler)
    workflow.add_node("query_handler", query_handler)
    workflow.add_node("format_response", format_response)
    workflow.add_node("log_interaction", log_interaction)

    # Add regular edges (no branching)
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "classify_message")

    # Route by confidence first (low → escalation), then by classification type
    workflow.add_conditional_edges(
        "classify_message",
        route_after_classification,
        {
            "escalation_handler": "escalation_handler",
            "positive_feedback_handler": "positive_feedback_handler",
            "negative_feedback_handler": "negative_feedback_handler",
            "query_handler": "query_handler",
        },
    )

    # All handlers (including escalation) go through format_response then logging
    workflow.add_edge("positive_feedback_handler", "format_response")
    workflow.add_edge("negative_feedback_handler", "format_response")
    workflow.add_edge("query_handler", "format_response")
    workflow.add_edge("escalation_handler", "format_response")
    workflow.add_edge("format_response", "log_interaction")
    workflow.add_edge("log_interaction", END)

    compiled = workflow.compile()

    print("✅ Workflow built with positive feedback, negative feedback, and query handlers!")
    print("   Flow: START -> validate -> classify -> [ROUTE] -> [HANDLER] -> END")

    return compiled

def test_workflow():
    """Test the workflow - currently only positive feedback handler is implemented."""
    print("\n" + "="*70)
    print("🧪 TESTING WORKFLOW (Positive Feedback Handler Only)")
    print("="*70)

    workflow = build_workflow()

    test_cases = [
        {
            "name": "Positive Feedback",
            "user_input": "I absolutely love your banking app! The interface is so easy to use.",
            "customer_id": "CUST001",
            "customer_name": "Alice Johnson"
        },
        {
            "name": "Negative Feedback",
            "user_input": "My credit card hasn't arrived yet and it's been 2 weeks. This is unacceptable.",
            "customer_id": "CUST002",
            "customer_name": "Bob Smith"
        },
        {
            "name": "Query",
            "user_input": "What is going on with my ticket #501197?",
            "customer_id": "CUST003",
            "customer_name": "Charlie Davis"
        },
        {
            "name": "Ambiguous / low confidence (escalation)",
            "user_input": "I'm not really sure how I feel about this whole situation. Maybe we can figure something out?",
            "customer_id": "CUST004",
            "customer_name": "Dana Lee"
        }
    ]
    # If the ambiguous case doesn't trigger escalation (model returns confidence >= 0.7),
    # temporarily set CONFIDENCE_THRESHOLD = 0.95 at the top of this file to force escalation.

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'='*70}")

        result = workflow.invoke(test_case)

        print(f"\n📤 RESULT:")
        print(f"   Classification: {result['classified_type']}")
        print(f"   Confidence: {result['classification_confidence']:.2f}")
        print(f"   Topic: {result['extracted_topic']}")
        print(f"   Handler: {result['agent_name']}")
        print()
        print(result["response"])

    print("\n" + "="*70)
    print("✅ TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_workflow()