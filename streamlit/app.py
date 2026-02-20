"""
Banking Customer Support AI Agent - Streamlit UI
Run from project root: streamlit run streamlit/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on path for workflow and db imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import html
import json
import uuid
import streamlit as st
import time
from datetime import datetime, timedelta

# Set page config
st.set_page_config(
    page_title="Banking Customer Support AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark green and cream theme
DARK_GREEN = "#1B4332"
MEDIUM_GREEN = "#2D6A4F"
CREAM_BG = "#FFF8E7"
CREAM_CARD = "#FFFBF0"
CREAM_TEXT = "#2D2D2D"
CREAM_LIGHT = "#FDF5E6"
SIDEBAR_TEXT = "#FFFBF0"  # Brighter cream/white for clear contrast on dark green

st.markdown("""
<style>
    /* Main app background - cream */
    .stApp, .main {
        background-color: %s;
    }
    
    /* Headers - dark green */
    h1, h2, h3 {
        color: %s;
    }
    
    /* Sidebar - dark green background, high-contrast cream/white text */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, %s 0%%, %s 100%%);
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stMetricLabel"],
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: %s !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: %s;
    }
    [data-testid="stSidebar"] .stExpander label {
        color: %s !important;
    }
    [data-testid="stSidebar"] .stExpander div,
    [data-testid="stSidebar"] .stExpander p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: %s !important;
    }
    
    /* Inputs - cream card, dark green border */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: %s !important;
        color: %s !important;
        border: 2px solid %s !important;
        border-radius: 8px;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background-color: %s !important;
        border: 2px solid %s;
        border-radius: 8px;
    }
    
    /* Primary button - dark green */
    .stButton > button {
        background-color: %s !important;
        color: %s !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 10px 24px;
    }
    .stButton > button:hover {
        background-color: %s !important;
        color: %s !important;
        border: none;
        transform: scale(1.02);
    }
    
    /* Body and label text - dark green */
    .stMarkdown, .stMarkdown p, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: %s !important;
    }
    
    /* Cards and containers */
    .metric-card {
        background-color: %s;
        border: 1px solid %s;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .result-box {
        background-color: %s;
        border-left: 4px solid %s;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
        white-space: pre-wrap;
        color: %s !important;
    }
    .detail-row {
        background-color: %s;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        color: %s;
    }
    
    /* Tabs - active: dark green bg + cream text; inactive: dark green text + cream card bg for clear differentiation */
    .stTabs [data-baseweb="tab-list"] {
        background-color: %s;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: %s;
        background-color: %s;
        border: 1px solid %s;
        border-radius: 6px;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: %s;
        color: %s;
    }
    .stTabs [aria-selected="true"] {
        background-color: %s !important;
        color: %s !important;
        border-color: %s;
    }
    
    /* Success / status */
    .status-ok { color: %s; font-weight: bold; }
    .status-warn { color: #B8860B; font-weight: bold; }
    
    /* Chat bubbles */
    .chat-container { padding: 12px 0; min-height: 200px; }
    .chat-bubble { max-width: 85%%; padding: 12px 16px; border-radius: 16px; margin: 8px 0; white-space: pre-wrap; word-wrap: break-word; }
    .chat-bubble-user { background: %s; color: %s; margin-left: auto; margin-right: 0; border-bottom-right-radius: 4px; }
    .chat-bubble-assistant { background: %s; color: %s; border: 1px solid %s; border-bottom-left-radius: 4px; }
    .chat-bubble time { font-size: 0.75rem; opacity: 0.8; display: block; margin-top: 6px; }
    .chat-input-area { padding: 16px 0; border-top: 1px solid %s; }
    .right-panel { padding-left: 24px; border-left: 1px solid %s; }
</style>
""" % (
    CREAM_BG, DARK_GREEN,
    DARK_GREEN, MEDIUM_GREEN, SIDEBAR_TEXT, SIDEBAR_TEXT, SIDEBAR_TEXT, SIDEBAR_TEXT,
    CREAM_CARD, DARK_GREEN, MEDIUM_GREEN,
    CREAM_CARD, MEDIUM_GREEN,
    MEDIUM_GREEN, CREAM_LIGHT, DARK_GREEN, CREAM_LIGHT,
    DARK_GREEN,
    CREAM_CARD, MEDIUM_GREEN,
    CREAM_CARD, MEDIUM_GREEN, DARK_GREEN,
    CREAM_CARD, DARK_GREEN,
    CREAM_CARD, DARK_GREEN, CREAM_CARD, MEDIUM_GREEN, CREAM_CARD, DARK_GREEN, MEDIUM_GREEN, CREAM_LIGHT, MEDIUM_GREEN,
    MEDIUM_GREEN,
    MEDIUM_GREEN, SIDEBAR_TEXT, CREAM_CARD, DARK_GREEN, MEDIUM_GREEN, MEDIUM_GREEN, MEDIUM_GREEN,
), unsafe_allow_html=True)


@st.cache_resource
def init_database():
    """Initialize database tables on first run."""
    from db.database import init_db
    init_db()
    return True


@st.cache_resource
def get_workflow():
    """Build and cache the compiled workflow."""
    from workflow.workflow import build_workflow
    return build_workflow()


def load_stats():
    """Load session stats from LogManager (last 7 days)."""
    try:
        from db.db_utils import LogManager
        return LogManager.get_stats(days=7)
    except Exception:
        return {
            "total_interactions": 0,
            "avg_confidence": 0,
            "by_classification": {},
            "avg_processing_time_ms": 0,
        }


def load_session_history(session_id):
    """Load chat history for a session from the DB (interaction logs). Returns list of {message, response, ...}."""
    from db.db_utils import SessionManager, LogManager
    hist = SessionManager.get_session_history(session_id)
    if not hist or not hist.interaction_logs_json:
        return []
    try:
        log_ids = json.loads(hist.interaction_logs_json)
    except Exception:
        return []
    if not log_ids:
        return []
    logs = LogManager.get_logs_by_ids(log_ids)
    return [
        {
            "message": log.input_message or "",
            "summary": (log.input_message or "")[:80],
            "classification": log.classification or "",
            "confidence": log.confidence or 0,
            "response": log.response or "",
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
        }
        for log in logs
    ]


def main():
    # Initialize database tables on startup (creates tables if they don't exist)
    init_database()
    
    # Session state for history, last result, and DB session (for SessionManager)
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_error" not in st.session_state:
        st.session_state.last_error = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Sidebar (left) – session stats, session list, and controls
    with st.sidebar:
        st.markdown("### 📊 Session stats")
        stats = load_stats()
        st.metric("Total queries (7d)", stats["total_interactions"])
        avg_conf = stats.get("avg_confidence") or 0
        st.metric("Avg confidence", f"{avg_conf * 100:.0f}%")
        by_cls = stats.get("by_classification") or {}
        tickets_created = by_cls.get("negative_feedback", 0)
        st.metric("Tickets created", tickets_created)

        st.markdown("---")
        st.markdown("### 📂 Sessions")
        try:
            from db.db_utils import SessionManager
            current_sid = st.session_state.session_id
            current_record = SessionManager.get_session_history(current_sid)
            if current_record and current_record.interaction_logs_json:
                try:
                    n_saved = len(json.loads(current_record.interaction_logs_json))
                except Exception:
                    n_saved = 0
            else:
                n_saved = 0
            current_label = f"Current: {current_sid[:8]}… ({n_saved} saved)" if n_saved else f"Current: {current_sid[:8]}… (new)"
            recent = SessionManager.list_sessions(limit=15)
            session_options = [current_label]
            session_ids = [current_sid]
            for row in recent:
                if row.session_id == current_sid:
                    continue
                try:
                    n = len(json.loads(row.interaction_logs_json or "[]"))
                except Exception:
                    n = 0
                ts = row.last_accessed.strftime("%b %d %H:%M") if getattr(row, "last_accessed", None) else ""
                session_options.append(f"{row.session_id[:8]}… ({n}) · {ts}")
                session_ids.append(row.session_id)
            chosen = st.selectbox(
                "Switch session",
                range(len(session_options)),
                format_func=lambda i: session_options[i],
                key="session_switch",
                help="Current session is created automatically when you send your first message.",
            )
            if chosen is not None and chosen > 0 and session_ids[chosen] != current_sid:
                st.session_state.session_id = session_ids[chosen]
                st.session_state.history = load_session_history(st.session_state.session_id)
                st.session_state.last_result = None
                st.session_state.last_error = None
                st.rerun()
        except Exception as e:
            st.caption(f"Session: {st.session_state.session_id[:8]}…")
            st.caption("(Could not load session list)")

        if st.button("New session", use_container_width=True, help="Start a new conversation session (saved when you send a message)"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.history = []
            st.session_state.last_result = None
            st.session_state.last_error = None
            st.rerun()
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.session_state.last_result = None
            st.session_state.last_error = None
            st.rerun()

    # No customer dropdown: use a single default so identity can come from the message (e.g. QueryAgent looks up by name in message)
    DEFAULT_CUSTOMER_ID = "GUEST"
    DEFAULT_CUSTOMER_NAME = "Guest"

    # Compact header
    st.markdown("""
        <h1 style="color: %s; font-size: 1.5rem; margin-bottom: 4px;">🏦 Banking Customer Support AI</h1>
        <p style="color: %s; font-size: 0.9rem; margin-bottom: 16px;">Classify and route customer messages.</p>
    """ % (DARK_GREEN, DARK_GREEN), unsafe_allow_html=True)

    # Main area: chat (~50%%) | gap | right panel (~25%%)
    col_chat, col_gap, col_right = st.columns([2, 0.5, 1])

    with col_chat:
        st.markdown("""
            <h2 style="color: %s; margin-bottom: 8px;">💬 Conversation</h2>
        """ % DARK_GREEN, unsafe_allow_html=True)

        # Chat history as bubbles
        history = st.session_state.history
        if history:
            for entry in history:
                user_msg = entry.get("message", entry.get("summary", "")) or ""
                asst_msg = entry.get("response", "") or ""
                ts = entry.get("timestamp", "")
                try:
                    t = datetime.fromisoformat(ts).strftime("%H:%M") if ts else ""
                except Exception:
                    t = ""
                st.markdown(
                    '<div class="chat-bubble chat-bubble-user">%s<time>%s</time></div>'
                    % (html.escape(user_msg), html.escape(t)),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="chat-bubble chat-bubble-assistant">%s<time>%s</time></div>'
                    % (html.escape(asst_msg), html.escape(t)),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="chat-container"><p style="color: %s;">No messages yet. Send a message below.</p></div>'
                % DARK_GREEN,
                unsafe_allow_html=True,
            )

        # Input area
        st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)
        message = st.text_area(
            "Message",
            placeholder="Enter the customer's message here...",
            height=100,
            key="message",
            label_visibility="visible",
        )
        submit = st.button("Submit", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if submit:
        if not message or not message.strip():
            st.error("Please enter a message.")
        else:
            with st.spinner("Classifying and routing…"):
                start = time.perf_counter()
                try:
                    # Build conversation history for LLM context (prior turns in this session)
                    conversation_history = []
                    for entry in st.session_state.history:
                        conversation_history.append({
                            "role": "user",
                            "content": entry.get("message", entry.get("summary", "")) or "",
                        })
                        conversation_history.append({
                            "role": "assistant",
                            "content": entry.get("response", "") or "",
                        })
                    workflow = get_workflow()
                    result = workflow.invoke({
                        "user_input": message.strip(),
                        "customer_id": DEFAULT_CUSTOMER_ID,
                        "customer_name": DEFAULT_CUSTOMER_NAME,
                        "session_id": st.session_state.session_id,
                        "conversation_history": conversation_history,
                    })
                    # Use workflow-computed processing time (includes all nodes); fall back to UI timing
                    if not result.get("processing_time_ms"):
                        result["processing_time_ms"] = int((time.perf_counter() - start) * 1000)
                    st.session_state.last_result = result
                    st.session_state.last_error = None
                    st.session_state.history.append({
                        "message": message.strip(),
                        "summary": message.strip()[:80],
                        "classification": result.get("classified_type", ""),
                        "confidence": result.get("classification_confidence", 0),
                        "response": result.get("response", ""),
                        "timestamp": datetime.now().isoformat(),
                    })
                except Exception as e:
                    st.session_state.last_error = str(e)
                    st.session_state.last_result = None

            st.rerun()

    # Right panel (~25%%) – current result stats, details, debug
    with col_right:
        st.markdown("""
            <div class="right-panel">
                <h3 style="color: %s;">📋 Current response</h3>
            </div>
        """ % DARK_GREEN, unsafe_allow_html=True)

        if st.session_state.last_error:
            st.error("An error occurred: " + st.session_state.last_error)

        result = st.session_state.last_result
        if result:
            st.metric("Classification", result.get("classified_type", "—"))
            conf = result.get("classification_confidence")
            st.metric("Confidence", f"{conf * 100:.0f}%" if conf is not None else "—")
            ms = result.get("processing_time_ms")
            st.metric("Time", f"{ms} ms" if ms is not None else "—")
            status = "✅ Success" if not st.session_state.last_error else "⚠️ Issues"
            st.metric("Status", status)

            st.markdown("**Details**")
            st.caption("Classification: " + str(result.get("classified_type") or "—"))
            st.caption("Topic: " + str(result.get("extracted_topic") or "—"))
            st.caption("Handler: " + str(result.get("agent_name") or "—"))
            if result.get("ticket_id"):
                st.caption("Ticket ID: " + str(result.get("ticket_id")))
            if result.get("ticket_status"):
                st.caption("Ticket status: " + str(result.get("ticket_status")))

            with st.expander("Debug"):
                st.json({
                    "classified_type": result.get("classified_type"),
                    "classification_confidence": result.get("classification_confidence"),
                    "extracted_topic": result.get("extracted_topic"),
                    "agent_name": result.get("agent_name"),
                    "ticket_id": result.get("ticket_id"),
                    "ticket_status": result.get("ticket_status"),
                    "processing_time_ms": result.get("processing_time_ms"),
                })
        else:
            st.caption("Submit a message to see classification, metrics and debug here.")


if __name__ == "__main__":
    main()
