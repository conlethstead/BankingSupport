from typing import TypedDict, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add parent directory to Python path so we can import agents module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our specialized agents
from agents.handlers import NegativeFeedbackAgent, PositiveFeedbackAgent, QueryAgent

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("PAID_OPENAI_API_KEY"))

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


class BankingAgentState(TypedDict):
    # Input
    user_input: str
    customer_id: str
    customer_name: str

    # Classification
    classified_type: str # query, positive_feedback, negative_feedback
    classification_confidence: float
    extracted_topic: str

    # Ticket info
    # ticket_id: str
    # ticket_status: str

    # Agent Response
    response: str
    agent_name: str # which agent handled the query
    

def validate_input(state):
    """Validate user input."""
    print("📥 [validate_input] Running validation...")

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
        "customer_name": customer_name
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
# ROUTING FUNCTION
# ============================================================================

def route_by_classification(state: BankingAgentState) -> str:
    """
    Router function that decides which handler to call based on classification.

    This is called by LangGraph's conditional_edges to determine the next node.

    :param state: Current workflow state
    :return: Name of the next node to execute
    """
    classified_type = state["classified_type"]

    print(f"🔀 [router] Routing to: {classified_type}_handler")

    # For now, only handle positive feedback
    # TODO: Add other handlers later
    if classified_type == "positive_feedback":
        return "positive_feedback_handler"
    elif classified_type == "negative_feedback":
        return "negative_feedback_handler"
    else:
        # Temporary: route everything else to positive feedback for now
        print(f"   ⚠️  Handler for '{classified_type}' not implemented yet, using positive_feedback")
        return "positive_feedback_handler"

    # elif classified_type == "negative_feedback":
    #     return "negative_feedback_handler"
    # else:  # query
    #     return "query_handler"


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


# def query_handler(state: BankingAgentState) -> dict:
#     """
#     Handler node for queries - delegates to QueryAgent.
#     """
#     return QueryAgent.handle(state)

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
    workflow.add_node("positive_feedback_handler", positive_feedback_handler)
    workflow.add_node("negative_feedback_handler", negative_feedback_handler)  # TODO: Add later
    # workflow.add_node("query_handler", query_handler)  # TODO: Add later

    # Add regular edges (no branching)
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "classify_message")

    # Add CONDITIONAL edge - this is where the routing happens!
    # For now, everything routes to positive_feedback_handler
    workflow.add_conditional_edges(
        "classify_message",  # Source node
        route_by_classification,  # Function that returns the next node name
        {
            # Map of possible return values to node names
            "positive_feedback_handler": "positive_feedback_handler",
            "negative_feedback_handler": "negative_feedback_handler",
            # "query_handler": "query_handler"  # TODO: Add later
        }
    )

    # Handler leads to END
    workflow.add_edge("positive_feedback_handler", END)
    # workflow.add_edge("negative_feedback_handler", END)  # TODO: Add later
    # workflow.add_edge("query_handler", END)  # TODO: Add later

    compiled = workflow.compile()

    print("✅ Workflow built with positive feedback handler only!")
    print("   Flow: START -> validate -> classify -> [ROUTE] -> positive_feedback_handler -> END")

    return compiled

def test_workflow():
    """Test the workflow - currently only positive feedback handler is implemented."""
    print("\n" + "="*70)
    print("🧪 TESTING WORKFLOW (Positive Feedback Handler Only)")
    print("="*70)

    workflow = build_workflow()

    # Test cases - all will route to positive feedback handler for now
    test_cases = [
        # {
        #     "name": "Positive Feedback",
        #     "user_input": "I absolutely love your banking app! The interface is so easy to use.",
        #     "customer_id": "CUST001",
        #     "customer_name": "Alice Johnson"
        # },
        {
            "name": "Negative Feedback",
            "user_input": "My credit card hasn't arrived yet and it's been 2 weeks. This is unacceptable.",
            "customer_id": "CUST002",
            "customer_name": "Bob Smith"
        },
        # {
        #     "name": "Query (Not Implemented Yet)",
        #     "user_input": "Can you check the status of my ticket number 123456?",
        #     "customer_id": "CUST003",
        #     "customer_name": "Charlie Davis"
        # }
    ]

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
        print(f"   Response: {result['response']}")

    print("\n" + "="*70)
    print("✅ TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_workflow()