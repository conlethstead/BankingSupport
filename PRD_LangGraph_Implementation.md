# Banking Customer Support AI Agent - Product Requirements Document

## Executive Summary

This document outlines the requirements for implementing a **Multi-Agent Banking Customer Support AI System** using LangGraph orchestration. The system will intelligently classify customer messages, route them to appropriate handlers, and manage support tickets through an integrated database.

---

## 1. Problem Statement

### Current Challenges
Modern digital banking platforms handle high-volume customer service interactions through fragmented systems that:
- Struggle to personalize responses based on customer sentiment
- Fail to provide timely status updates on support tickets
- Cannot effectively differentiate between feedback and queries
- Require manual intervention for ticket routing and classification

### Business Impact
- **Increased operational costs** from manual processing
- **Poor customer satisfaction** due to delayed responses
- **Inconsistent communication** across support channels
- **Lost insights** from unstructured feedback data

---

## 2. Project Objectives

### Primary Goals
1. **Automate message classification** into three categories: positive feedback, negative feedback, or query
2. **Reduce manual effort** through intelligent agent routing
3. **Improve response time** with immediate, context-aware replies
4. **Maintain audit trail** of all customer interactions for compliance
5. **Enable scalability** to handle increasing volume without proportional cost increase

### Success Metrics
- **Classification Accuracy**: ≥ 95% accuracy on test dataset
- **Response Time**: < 2 seconds per interaction
- **Ticket Creation Rate**: 100% for valid negative feedback
- **Routing Success**: 100% correct agent routing based on classification
- **Uptime**: 99.5% availability
- **User Satisfaction**: Collect feedback on response quality

---

## 3. Proposed Solution: LangGraph Architecture

### Architecture Overview

LangGraph provides explicit workflow management with state persistence, making it ideal for banking customer support workflows requiring audit trails and compliance logging.

```
User Input (Streamlit UI)
    ↓
LangGraph Workflow
    ├─ Input Validation Node
    ├─ Classification Node (LLM)
    ├─ Conditional Routing
    │   ├─ Positive Feedback Handler
    │   ├─ Negative Feedback Handler
    │   ├─ Query Handler
    │   └─ Error Handler
    ├─ Database Operations
    └─ Response Formatting & Logging
    ↓
Output (Streamlit UI)
```

### Why LangGraph?
✅ **Explicit routing** - No ambiguity in agent selection  
✅ **State persistence** - Full audit trail for compliance  
✅ **Error handling** - Built-in retry and fallback mechanisms  
✅ **Debugging** - Easy to visualize and trace execution flow  
✅ **Production-ready** - Industry standard for multi-agent workflows  

---

## 4. System Architecture

### 4.1 State Schema

```python
class BankingAgentState(TypedDict):
    # Input
    input_message: str
    customer_id: str
    customer_name: str
    
    # Classification Results
    classified_type: str  # "positive_feedback" | "negative_feedback" | "query"
    classification_confidence: float  # 0.0 - 1.0
    extracted_topic: str  # Topic extracted from message
    
    # Ticket Information (for negative feedback/queries)
    ticket_id: str  # Generated or extracted
    ticket_status: str  # "unresolved" | "in_progress" | "resolved"
    
    # Agent Response
    response: str  # Final response to customer
    agent_name: str  # Which agent handled it
    
    # Metadata
    errors: list[dict]  # Any errors that occurred
    timestamp: datetime
    processing_time_ms: float
```

### 4.2 Graph Nodes

#### Node 1: Input Validation
- **Input**: Raw user message
- **Task**: Validate message is not empty, has reasonable length
- **Output**: Validated message or error
- **Next**: Classification Node or Error Handler

#### Node 2: Classification Node
- **Input**: Validated user message, customer context
- **Task**: Call LLM to classify message into three categories
- **Prompt**: 
  ```
  Classify the following banking customer message into ONE category:
  - "positive_feedback": Customer praising service or satisfied
  - "negative_feedback": Customer expressing dissatisfaction
  - "query": Customer asking for information or ticket status
  
  Message: {message}
  
  Return JSON: {"category": "...", "confidence": 0.0-1.0, "topic": "..."}
  ```
- **Output**: Classification type, confidence score, extracted topic
- **Next**: Conditional Router

#### Node 3: Conditional Router
- **Input**: Classification type from Node 2
- **Task**: Route to appropriate handler based on classification
- **Routes**:
  - `positive_feedback` → Positive Feedback Handler
  - `negative_feedback` → Negative Feedback Handler
  - `query` → Query Handler
  - `uncertain` (confidence < 0.7) → Escalation Handler

#### Node 4a: Positive Feedback Handler
- **Input**: Message, customer name
- **Task**: 
  - Generate warm, personalized thank-you message
  - Call LLM with prompt
- **Prompt Template**:
  ```
  Generate a warm, personalized thank-you message for a banking customer.
  Customer Name: {customer_name}
  Original Message: {message}
  
  Requirements:
  - 1-2 sentences max
  - Professional but friendly tone
  - Reference their specific issue if mentioned
  
  Response:
  ```
- **Output**: Formatted response message
- **Database**: Log interaction (no ticket creation)
- **Next**: Response Formatting Node

#### Node 4b: Negative Feedback Handler
- **Input**: Message, customer name
- **Task**:
  - Generate unique 6-digit ticket number
  - Create new support ticket in database
  - Generate empathetic response with ticket number
- **Ticket Generation**: 
  ```
  ticket_id = random 6-digit number (100000-999999)
  Verify uniqueness in database
  ```
- **Prompt Template**:
  ```
  Generate an empathetic response to a banking customer's complaint.
  Customer Name: {customer_name}
  Issue: {message}
  Ticket ID: {ticket_id}
  
  Requirements:
  - Apologize for the inconvenience
  - Acknowledge their issue specifically
  - Provide ticket number clearly
  - Assure them of follow-up
  
  Format: "We apologize for the inconvenience. A new ticket #{ticket_id} has been created..."
  ```
- **Database Operations**:
  ```
  INSERT INTO support_tickets (
    ticket_id, customer_id, customer_name, 
    message_content, classification, status, 
    created_at, agent_response
  ) VALUES (...)
  ```
- **Output**: Formatted response with ticket number
- **Next**: Response Formatting Node

#### Node 4c: Query Handler
- **Input**: Message, customer_id
- **Task**:
  - Extract ticket number from message
  - Query database for ticket status
  - Generate response with ticket information
- **Extraction Logic**:
  ```
  Use regex to find 6-digit numbers in message
  OR use LLM to extract ticket reference
  Look for patterns: "ticket #123456", "ticket 123456", etc.
  ```
- **Database Query**:
  ```
  SELECT status, created_at, resolved_at 
  FROM support_tickets 
  WHERE ticket_id = {extracted_id}
  ```
- **Prompt Template**:
  ```
  Generate a professional status update response.
  Ticket ID: {ticket_id}
  Current Status: {status}
  Created: {created_at}
  Resolved: {resolved_at}
  
  Format: "Your ticket #{ticket_id} is currently marked as: {status}."
  Include estimated resolution time if status is "in_progress".
  ```
- **Output**: Formatted response with ticket status
- **Next**: Response Formatting Node

#### Node 4d: Error/Escalation Handler
- **Input**: Low confidence classification or extraction error
- **Task**: 
  - Log error with context
  - Generate escalation message
  - Mark for manual review
- **Output**: Escalation response
- **Next**: Response Formatting Node

#### Node 5: Response Formatting Node
- **Input**: Raw response from handler, state information
- **Task**:
  - Format response for display
  - Add context if needed
  - Ensure consistency
- **Output**: Final formatted response
- **Next**: Logging Node

#### Node 6: Logging Node
- **Input**: Complete state with response
- **Task**:
  - Store interaction log in database
  - Update session history
  - Record metrics (processing time, success/failure)
- **Database Operations**:
  ```
  INSERT INTO interaction_logs (
    customer_id, input_message, classification, 
    confidence, ticket_id, agent_path, response,
    timestamp, processing_time_ms
  ) VALUES (...)
  ```
- **Output**: Logged state
- **Next**: Return to UI

### 4.3 Graph Edges

```
Input Validation → Classification (always)
Classification → Conditional Router (always)
Conditional Router → Positive Feedback Handler (if positive_feedback)
Conditional Router → Negative Feedback Handler (if negative_feedback)
Conditional Router → Query Handler (if query)
Conditional Router → Escalation Handler (if uncertain)
All Handlers → Response Formatting (always)
Response Formatting → Logging (always)
Logging → End (always)
```

---

## 5. Database Schema

### Table 1: support_tickets

```sql
CREATE TABLE support_tickets (
    ticket_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(255),
    message_content TEXT NOT NULL,
    classification VARCHAR(50),
    status VARCHAR(50) DEFAULT 'unresolved',  -- unresolved, in_progress, resolved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    agent_response TEXT,
    customer_feedback VARCHAR(50),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);
```

### Table 2: interaction_logs

```sql
CREATE TABLE interaction_logs (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id VARCHAR(100) NOT NULL,
    input_message TEXT NOT NULL,
    classification VARCHAR(50),
    confidence FLOAT,
    extracted_topic VARCHAR(255),
    ticket_id VARCHAR(10) NULL,
    agent_path VARCHAR(255),
    response TEXT,
    processing_time_ms INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    errors TEXT NULL,
    INDEX idx_customer (customer_id),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(ticket_id)
);
```

### Table 3: session_history

```sql
CREATE TABLE session_history (
    session_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100),
    interaction_logs JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    session_context JSON
);
```

---

## 6. API Specifications

### Classification Endpoint

**Input:**
```python
{
    "message": str,
    "customer_id": str,
    "customer_name": str
}
```

**Output:**
```python
{
    "classified_type": "positive_feedback" | "negative_feedback" | "query",
    "confidence": float,
    "extracted_topic": str,
    "ticket_id": str | None,
    "response": str,
    "timestamp": datetime
}
```

---

## 7. Streamlit UI Requirements

### 7.1 Main Interface

**Layout:**
- **Header**: "Banking Customer Support AI Agent"
- **Sidebar**: Session stats, recent queries, clear history
- **Main Area**: Input form, results display, tabs for details

### 7.2 Components

#### Input Section
- Text input: "Enter your message:"
- Dropdown: Customer name selection
- Button: "Submit" (disabled during processing)
- Loading indicator during workflow execution

#### Results Display
- **Metrics Row**: 
  - Classification Type (positive/negative/query)
  - Confidence Score (%)
  - Processing Time (ms)
  - Status (✅ Success or ⚠️ Issues)

- **Tabs**:
  - **Response**: Final message to customer
  - **Details**: Classification info, ticket ID if applicable
  - **Debug**: Execution path, prompts used, errors

#### Sidebar
- **Session Stats**:
  - Total Queries: {count}
  - Avg Confidence: {%}
  - Tickets Created: {count}
  
- **Recent Queries** (last 5):
  - Expandable list of recent interactions
  - Quick stats per query
  
- **Action Buttons**:
  - "Clear History" button
  - "Export Session" button

### 7.3 Error Handling Display
- Error severity levels: Info, Warning, Error, Critical
- Error details expandable
- Suggestion for resolution

---

## 8. Development Phases

### Current Implementation Status (as of 2026-02-11)

This section reflects the current codebase state so you can track progress step by step.

**Implemented in code**
- **LangGraph workflow (core)**: Input validation + LLM classification + conditional routing
- **Handlers**: Positive feedback handler and negative feedback handler implemented (LLM responses)
- **Query handler**: Implemented in [Capstone/Banking/agents/handlers.py](Capstone/Banking/agents/handlers.py), not yet wired into the LangGraph workflow
- **Database**: SQLite schema + SQLAlchemy models + ticket/log/session utilities
- **Streamlit UI**: Basic UI scaffolding and styling (no workflow integration yet)

**Partially implemented / in progress**
- **Routing**: Query route not wired; fallback currently routes to positive handler
- **Ticket creation**: Placeholder ticket ID in negative handler; DB call is TODO
- **Logging**: Logging utilities exist, but no logging node in LangGraph yet
- **Response formatting**: Not yet a dedicated node

**Not implemented yet**
- **Escalation/error handler**
- **Session history integration**
- **Full end-to-end UI integration**
- **Evaluation/testing suite**

### Phase 1: Core Framework (Week 1-2)
- [x] LangGraph installation and setup
- [x] State schema definition (core fields)
- [x] Database schema creation (SQLite + SQLAlchemy models)
- [x] Input validation node implementation
- [x] Classification node implementation with LLM integration

### Phase 2: Handlers (Week 3-4)
- [x] Positive feedback handler
- [x] Negative feedback handler (uses placeholder ticket ID)
- [ ] Query handler (implemented but not wired in workflow)
- [ ] Error/escalation handler
- [ ] Response formatting node

### Phase 3: Integration (Week 5-6)
- [x] Database connection and operations (utilities + schema)
- [ ] Session management
- [ ] Logging and monitoring (utilities exist; workflow node not added)
- [x] Graph assembly and testing (basic workflow test script)
- [ ] Error handling and fallbacks

### Phase 4: UI & Frontend (Week 7-8)
- [x] Streamlit app scaffolding
- [ ] Input form and controls
- [ ] Results display and formatting
- [ ] Session history sidebar
- [ ] Debug/trace view

### Phase 5: Evaluation & Testing (Week 9-10)
- [ ] Test case development (50+ test cases)
- [ ] Classification accuracy evaluation
- [ ] Routing correctness validation
- [ ] Response quality assessment
- [ ] Load testing

### Phase 6: Deployment & Polish (Week 11-12)
- [ ] Environment configuration
- [ ] Documentation
- [ ] Performance optimization
- [ ] Deployment to staging
- [ ] Production readiness review

---

## 9. Evaluation Metrics

### 9.1 Functional Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Classification Accuracy | ≥ 95% | Test on 500+ labeled examples |
| Routing Correctness | 100% | Verify agent routing logic |
| Ticket Creation Success | 100% | Negative feedback → ticket created |
| Query Resolution | ≥ 90% | Successful ticket status retrieval |
| Response Time | < 2s | End-to-end latency |

### 9.2 Quality Metrics

| Metric | Method | Acceptance |
|--------|--------|-----------|
| Response Empathy | Human evaluation (5-point scale) | ≥ 4.0 avg for negative feedback |
| Response Clarity | Human evaluation | ≥ 90% responses rated "clear" |
| Prompt Relevance | Human review | 100% of prompts appropriate |
| Error Handling | Manual testing | All errors logged, no crashes |

### 9.3 Performance Metrics

| Metric | Target |
|--------|--------|
| API Response Time (p95) | < 1500ms |
| Database Query Time | < 200ms |
| LLM Call Time | < 1s |
| Uptime | 99.5% |
| Error Rate | < 1% |

### 9.4 Test Coverage

- **Unit Tests**: ≥ 80% code coverage
- **Integration Tests**: All node combinations
- **End-to-End Tests**: 50+ realistic scenarios
- **Edge Cases**: Malformed input, empty messages, missing data

---

## 10. Test Scenarios

### Positive Feedback Examples
```
1. "Thanks for resolving my credit card issue quickly!"
2. "Great customer service, appreciate your help"
3. "Very satisfied with the support I received"
4. "You've been wonderful, thank you so much!"
```

### Negative Feedback Examples
```
1. "My debit card replacement still hasn't arrived"
2. "I've been waiting 3 days with no response"
3. "This is unacceptable, I'm very frustrated"
4. "Your system keeps rejecting my login attempts"
```

### Query Examples
```
1. "Could you check the status of ticket 650932?"
2. "What's the status of my ticket #784521?"
3. "Can you give me an update on ticket 123456?"
4. "Is ticket 999999 resolved yet?"
```

### Edge Cases
```
1. Empty message: ""
2. Ambiguous: "I need help with a ticket"
3. Multiple issues: "Ticket 123456 is still open and my card hasn't arrived"
4. Malformed ticket: "Check ticket 999" (only 3 digits)
5. Profanity/abuse: Handle gracefully with escalation
```

---

## 11. LLM Requirements

### Model Selection
- **Recommended**: GPT-4 or Claude 3.5 (high accuracy for classification)
- **Alternative**: GPT-3.5 Turbo (cost-effective, good performance)
- **Fallback**: Local model option via Ollama

### Prompt Engineering
- Classify accuracy: Test multiple prompt variations
- Few-shot examples in classification prompts
- Temperature: 0.3 (low, for consistency)
- Max tokens: 150 (for concise responses)

### API Calls Per Interaction
- Minimal configuration: 1 LLM call (classification)
- Response generation: 1 LLM call (response generation)
- Total: 2 API calls per interaction

---

## 12. Compliance & Logging

### Audit Trail Requirements
- All customer interactions logged with timestamp
- Complete state tracking for each interaction
- Agent decision paths recorded
- All database modifications timestamped
- Error logs retained for 90 days

### Data Privacy
- No sensitive customer data in logs (mask PII)
- Secure database connections (SSL/TLS)
- Access controls on support_tickets table
- GDPR compliance for data retention

### Error Logging
- All errors captured with:
  - Timestamp
  - Error type and message
  - Stack trace
  - Input that caused error
  - Agent state at time of error

## 15. Appendix: Implementation Checklist

### Technology Stack
- [x] Python 3.10+
- [ ] LangGraph
- [ ] LangChain
- [ ] Streamlit
- [ ] OpenAI API (or alternative LLM)
- [ ] SQLAlchemy
- [ ] SQLite/PostgreSQL

### Dependencies (requirements.txt)
```
langgraph==0.1.0+
langchain==0.1.0+
langchain-openai==0.1.0+
streamlit==1.28.0+
sqlalchemy==2.0+
python-dotenv==1.0+
pydantic==2.0+
```

### Configuration Files
- `.env`: API keys, database URL, model selection
- `config.yaml`: Model parameters, prompt templates, thresholds
- `prompts.yaml`: All LLM prompts centralized

### Deployment
- Docker container for production
- Environment variables for configuration
- Database migrations script
- Logging to stdout/file

---

## Sign-Off

This PRD defines the complete requirements for the Banking Customer Support AI Agent using LangGraph orchestration. The LangGraph architecture provides the transparency, audit trail, and error handling required for a production banking system.
