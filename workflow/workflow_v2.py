"""
Banking Customer Support AI - Classification Implementation
Phase 2: Adding LLM-based message classification
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

client = OpenAI(api_key=os.getenv("PAID_OPENAI_API_KEY"))


# ============================================================================
# PYDANTIC MODEL FOR CLASSIFICATION
# ============================================================================

class MessageClassification(BaseModel):
    """
    Structured output model for banking message classification.

    Attributes:
        classified_type: The message type (positive_feedback, negative_feedback, query)
        confidence: Confidence score between 0.0 and 1.0
        reasoning: Brief explanation of the classification decision
        extracted_topic: The main topic/subject identified in message
    """
    classified_type: Literal["positive_feedback", "negative_feedback", "query"] = Field(
        ...,
        description="Classification: positive_feedback, negative_feedback, or query"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for classification (0-1)"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this classification was chosen"
    )
    extracted_topic: str = Field(
        ...,
        description="Main topic or subject identified in the message"
    )


# ============================================================================
# STATE DEFINITION
# ============================================================================

class BankingAgentState(TypedDict):
    """State that flows through our workflow."""
    # Inputs
    user_input: str
    customer_id: str
    customer_name: str

    # Classification results
    classified_type: str  # positive_feedback, negative_feedback, query
    classification_confidence: float
    extracted_topic: str

    # Outputs
    response: str
    agent_name: str


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def validate_input(state: BankingAgentState) -> dict:
    """
    Node 1: Validate that we have all required inputs.
    """
    print("📥 [validate_input] Running validation...")

    user_input = state.get("user_input", "").strip()
    customer_id = state.get("customer_id", "").strip()
    customer_name = state.get("customer_name", "").strip()

    if not user_input:
        raise ValueError("❌ User input cannot be empty.")
    if not customer_id:
        raise ValueError("❌ Customer ID cannot be empty.")
    if not customer_name:
        raise ValueError("❌ Customer name cannot be empty.")

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
    Node 2: Classify the customer message using LLM.

    This determines if the message is:
    - positive_feedback: Customer is happy, praising the service
    - negative_feedback: Customer has a complaint or issue
    - query: Customer is asking about ticket status
    """
    print("🔍 [classify_message] Classifying message...")

    user_input = state["user_input"]

    # System prompt for classification
    system_prompt = """You are a classification expert for a banking customer support system.

Your task is to classify customer messages into three categories:

1. **positive_feedback**: Messages expressing satisfaction, praise, thanks, or positive experiences.
   Examples: "I love your app!", "Great service!", "Thank you for helping me"

2. **negative_feedback**: Messages with complaints, problems, issues, or dissatisfaction.
   Examples: "My card hasn't arrived", "I'm unhappy with the fees", "This is frustrating"

3. **query**: Messages asking about the status of a support ticket.
   Examples: "What's the status of ticket 123456?", "Any update on my issue?", "Check ticket status"

Analyze the message and provide:
- classified_type: One of "positive_feedback", "negative_feedback", or "query"
- confidence: Your confidence in this classification (0.0 to 1.0)
- reasoning: Brief explanation of your decision
- extracted_topic: The main subject/topic of the message"""

    user_prompt = f"""Classify this customer message: "{user_input}"

Provide your classification in this exact format:
- classified_type: [positive_feedback/negative_feedback/query]
- confidence: [0.0-1.0]
- reasoning: [your explanation]
- extracted_topic: [main topic]"""

    try:
        # Call the LLM
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for consistent classification
            max_tokens=200
        )

        # Extract response content
        response_content = response.choices[0].message.content
        print(f"   LLM Response:\n{response_content}")

        # Parse the response
        classification = parse_classification_response(response_content, user_input)

        print(f"✅ [classify_message] Classification complete!")
        print(f"   - Type: {classification.classified_type}")
        print(f"   - Confidence: {classification.confidence:.2f}")
        print(f"   - Topic: {classification.extracted_topic}")

        return {
            "classified_type": classification.classified_type,
            "classification_confidence": classification.confidence,
            "extracted_topic": classification.extracted_topic
        }

    except Exception as e:
        print(f"❌ Error during classification: {e}")
        # Fallback to negative_feedback (safe default - creates a ticket)
        return {
            "classified_type": "negative_feedback",
            "classification_confidence": 0.5,
            "extracted_topic": user_input[:50]
        }


def parse_classification_response(response_text: str, original_message: str) -> MessageClassification:
    """
    Parse the LLM's text response into a MessageClassification object.
    """
    import re

    # Initialize defaults
    classified_type = "negative_feedback"  # Safe default
    confidence = 0.5
    reasoning = response_text
    extracted_topic = original_message[:50]

    # Parse the response
    lines = response_text.lower().split('\n')

    for line in lines:
        # Extract classified_type
        if 'classified_type' in line or 'classification' in line:
            if 'positive_feedback' in line or 'positive' in line:
                classified_type = "positive_feedback"
            elif 'query' in line and 'feedback' not in line:
                classified_type = "query"
            elif 'negative_feedback' in line or 'negative' in line:
                classified_type = "negative_feedback"

        # Extract confidence
        if 'confidence' in line:
            numbers = re.findall(r'0?\.\d+|1\.0|0|1', line)
            if numbers:
                confidence = float(numbers[0])

        # Extract reasoning
        if 'reasoning' in line:
            reasoning = line.split(':', 1)[-1].strip()

        # Extract topic
        if 'topic' in line:
            extracted_topic = line.split(':', 1)[-1].strip()

    return MessageClassification(
        classified_type=classified_type,
        confidence=confidence,
        reasoning=reasoning if reasoning else response_text,
        extracted_topic=extracted_topic if extracted_topic else original_message[:50]
    )


def generate_simple_response(state: BankingAgentState) -> dict:
    """
    Node 3: Generate a simple response based on classification.

    For now, this just echoes back what we classified.
    Later, we'll route to different handlers.
    """
    print("💬 [generate_simple_response] Generating response...")

    customer_name = state["customer_name"]
    classified_type = state["classified_type"]
    extracted_topic = state["extracted_topic"]

    # Simple responses based on classification
    if classified_type == "positive_feedback":
        response = f"Thank you for your positive feedback, {customer_name}! We're glad you're happy with our service."
    elif classified_type == "negative_feedback":
        response = f"We're sorry to hear about your issue, {customer_name}. We've created a support ticket for: {extracted_topic}"
    else:  # query
        response = f"Hello {customer_name}, I can help you check your ticket status regarding: {extracted_topic}"

    print(f"✅ [generate_simple_response] Response created!")
    print(f"   - Response: {response}")

    return {
        "response": response,
        "agent_name": "simple_classifier"
    }


# ============================================================================
# BUILD WORKFLOW
# ============================================================================

def build_workflow():
    """
    Build the workflow with classification.

    Flow: START -> validate_input -> classify_message -> generate_response -> END
    """
    print("\n🔧 Building workflow with classification...")

    workflow = StateGraph(BankingAgentState)

    # Add nodes
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("classify_message", classify_message)
    workflow.add_node("generate_response", generate_simple_response)

    # Define edges
    workflow.add_edge(START, "validate_input")
    workflow.add_edge("validate_input", "classify_message")
    workflow.add_edge("classify_message", "generate_response")
    workflow.add_edge("generate_response", END)

    compiled_workflow = workflow.compile()

    print("✅ Workflow built successfully!")
    print("   Flow: START -> validate -> classify -> respond -> END")

    return compiled_workflow


# ============================================================================
# TEST THE WORKFLOW
# ============================================================================

def test_workflow():
    """
    Test the classification workflow with different message types.
    """
    print("\n" + "="*70)
    print("🧪 TESTING CLASSIFICATION WORKFLOW")
    print("="*70)

    workflow = build_workflow()

    # Test cases for each classification type
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
            "user_input": "Can you check the status of my ticket number 123456?",
            "customer_id": "CUST003",
            "customer_name": "Charlie Davis"
        }
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
        print(f"   Response: {result['response']}")

    print("\n" + "="*70)
    print("✅ TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_workflow()
