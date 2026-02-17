# Banking Customer Support Database - Quick Reference

## Setup Summary

✅ **Database Type**: SQLite (file-based, zero server setup)  
✅ **Location**: `db/banking_support.db`  
✅ **Tables**: 3 tables with proper relationships and indexes  
✅ **Package**: SQLAlchemy 2.0+ for ORM

---

## Quick Start

### 1. Import what you need

```python
from db.database import get_session, SupportTicket, InteractionLog
from db.db_utils import TicketManager, LogManager, SessionManager
```

### 2. Common operations

#### Create a support ticket
```python
ticket_id = TicketManager.create_ticket(
    customer_id="CUST001",
    customer_name="John Smith",
    message_content="My card hasn't arrived",
    classification="negative_feedback"
)
print(f"Ticket created: {ticket_id}")
```

#### Get ticket status
```python
ticket = TicketManager.get_ticket(ticket_id="123456")
print(f"Status: {ticket.status}")
```

#### Log an interaction
```python
log_id = LogManager.log_interaction(
    customer_id="CUST001",
    input_message="Where's my card?",
    classification="query",
    confidence=0.95,
    extracted_topic="card_status",
    ticket_id="123456",
    agent_path="query_handler",
    response="Your ticket #123456 is in progress.",
    processing_time_ms=340
)
```

#### Update ticket status
```python
TicketManager.update_ticket_status("123456", "in_progress")
```

#### Get customer's interaction history
```python
logs = LogManager.get_logs_by_customer("CUST001", limit=10)
for log in logs:
    print(f"{log.timestamp}: {log.classification} (confidence: {log.confidence})")
```

#### Get statistics
```python
stats = LogManager.get_stats(days=7)
print(f"Interactions this week: {stats['total_interactions']}")
print(f"By type: {stats['by_classification']}")
print(f"Avg confidence: {stats['avg_confidence']:.2%}")
```

---

## Database Schema

### Table: support_tickets
| Column | Type | Notes |
|--------|------|-------|
| ticket_id | VARCHAR(10) | Primary key, auto-generated |
| customer_id | VARCHAR(100) | Indexed |
| customer_name | VARCHAR(255) | |
| message_content | TEXT | Original customer message |
| classification | VARCHAR(50) | negative_feedback, positive_feedback, query |
| status | VARCHAR(50) | unresolved, in_progress, resolved |
| created_at | DATETIME | Indexed, auto-set |
| resolved_at | DATETIME | NULL until resolved |
| agent_response | TEXT | Response sent to customer |

### Table: interaction_logs
| Column | Type | Notes |
|--------|------|-------|
| log_id | INT | Primary key, auto-increment |
| customer_id | VARCHAR(100) | Indexed |
| input_message | TEXT | Customer input |
| classification | VARCHAR(50) | Detected type |
| confidence | FLOAT | 0.0-1.0 |
| extracted_topic | VARCHAR(255) | |
| ticket_id | VARCHAR(10) | Foreign key (optional) |
| agent_path | VARCHAR(255) | Which handler processed it |
| response | TEXT | Generated response |
| processing_time_ms | INT | Latency |
| timestamp | DATETIME | Indexed, auto-set |

### Table: session_history
| Column | Type | Notes |
|--------|------|-------|
| session_id | VARCHAR(100) | Primary key |
| customer_id | VARCHAR(100) | Indexed |
| interaction_logs_json | TEXT | JSON array of log IDs |
| created_at | DATETIME | Session start |
| last_accessed | DATETIME | Last interaction |

---

## Why SQLite?

For your capstone with ~100 entries:
- ✅ **Zero infrastructure** - Just a file
- ✅ **Fast queries** - SQLite is optimized for small datasets
- ✅ **Transactional** - ACID compliance
- ✅ **Easy to backup** - Just copy the .db file
- ✅ **Easy to deploy** - No database server to manage
- ✅ **SQLAlchemy compatible** - Same code works if you migrate later to PostgreSQL

---

## Upgrading Later (if needed)

If you grow beyond SQLite, you can switch to PostgreSQL with minimal code changes:

```python
# Current (SQLite)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Switch to PostgreSQL (same Python code)
DATABASE_URL = "postgresql://user:password@localhost/banking_support"
```

SQLAlchemy handles the differences automatically.

---

## Tips

- **Always use `get_session()`** - It manages connections properly
- **Session is closed** in all utility functions - They're safe to call repeatedly
- **Ticket IDs are 6 digits** - TicketManager auto-generates unique ones
- **Timestamps are UTC** - All stored as ISO 8601
- **Indexes on key columns** - customer_id, status, and created_at for fast queries
- **Test data included** - 2 sample tickets for development

---

## Next Steps for Your LangGraph

In your LangGraph nodes, use it like:

```python
# In Classification Node
from db.db_utils import TicketManager

# In Response Handler
ticket_id = TicketManager.create_ticket(
    customer_id=state["customer_id"],
    customer_name=state["customer_name"],
    message_content=state["input_message"],
    classification=state["classified_type"]
)

# In Logging Node
from db.db_utils import LogManager
LogManager.log_interaction(
    customer_id=state["customer_id"],
    input_message=state["input_message"],
    classification=state["classified_type"],
    confidence=state["classification_confidence"],
    extracted_topic=state["extracted_topic"],
    ticket_id=state.get("ticket_id"),
    agent_path=state["agent_name"],
    response=state["response"],
    processing_time_ms=int(state["processing_time_ms"])
)
```

Happy building! 🚀
