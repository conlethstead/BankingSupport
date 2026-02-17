import streamlit as st

# Set page config
st.set_page_config(
    page_title="Banking Customer Support AI",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for off-white, grass green, and warm accent theme
st.markdown("""
    <style>
    /* Off-white background */
    .stApp {
        background-color: #F5F3F0;
    }
    
    /* Main container */
    .main {
        background-color: #F5F3F0;
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: #6BB76B;
    }
    
    /* Input box styling */
    .stTextInput > div > div > input {
        background-color: #FFFFFF;
        color: #2D2D2D;
        border: 2px solid #6BB76B;
        border-radius: 8px;
    }
    
    /* Text area styling */
    .stTextArea > div > div > textarea {
        background-color: #FFFFFF;
        color: #2D2D2D;
        border: 2px solid #6BB76B;
        border-radius: 8px;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #6BB76B;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        padding: 10px 20px;
    }
    
    .stButton > button:hover {
        background-color: #5AA65A;
        transform: scale(1.02);
    }
    
    /* Sidebar styling */
    .stSidebar {
        background-color: #FFFBF7;
        border-right: 2px solid #6BB76B;
    }
    
    /* Text color */
    .stMarkdown {
        color: #2D2D2D;
    }
    
    /* Metric box styling */
    .metric-box {
        background-color: #FFFFFF;
        border-left: 4px solid #D97A5C;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Success message */
    .success-box {
        background-color: rgba(107, 183, 107, 0.1);
        border-left: 4px solid #6BB76B;
        padding: 15px;
        border-radius: 8px;
        color: #5AA65A;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <h1 style="color: #6BB76B; text-align: center; margin-bottom: 30px;">
    🏦 Banking Customer Support AI Agent
    </h1>
""", unsafe_allow_html=True)

# Main layout
col1, col2 = st.columns([2, 1])

with col1:
    # Input section
    st.markdown("""
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 8px; border: 2px solid #6BB76B; margin-bottom: 20px;">
            <h2 style="color: #6BB76B; margin-top: 0;">📝 Customer Message</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Customer name input
    customer_name = st.text_input(
        "Customer Name",
        placeholder="Enter customer name",
        key="customer_name"
    )
    
    # Customer ID input
    customer_id = st.text_input(
        "Customer ID",
        placeholder="Enter customer ID",
        key="customer_id"
    )
    
    # Message input
    message = st.text_area(
        "Message",
        placeholder="Enter customer message here...",
        height=150,
        key="message"
    )
    
    # Submit button
    col_button, col_space = st.columns([1, 4])
    with col_button:
        submit_button = st.button("🚀 Submit", use_container_width=True)
    
    if submit_button:
        if message.strip():
            st.markdown("""
                <div class="success-box">
                    <strong>✓ Message received!</strong><br>
                    Processing: <em>{}</em>
                </div>
            """.format(message[:50] + "..." if len(message) > 50 else message), unsafe_allow_html=True)
        else:
            st.warning("Please enter a message")

with col2:
    # Sidebar stats
    st.markdown("""
        <div style="background-color: #FFFFFF; padding: 20px; border-radius: 8px; border: 2px solid #6BB76B;">
            <h3 style="color: #6BB76B; margin-top: 0;">📊 Stats</h3>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="metric-box">
            <strong style="color: #D97A5C;">Total Interactions</strong><br>
            <span style="font-size: 24px; font-weight: bold; color: #6BB76B;">0</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="metric-box">
            <strong style="color: #D97A5C;">Avg Confidence</strong><br>
            <span style="font-size: 24px; font-weight: bold; color: #6BB76B;">--</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="metric-box">
            <strong style="color: #D97A5C;">Tickets Created</strong><br>
            <span style="font-size: 24px; font-weight: bold; color: #6BB76B;">0</span>
        </div>
    """, unsafe_allow_html=True)

# Footer section
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #888; margin-top: 30px;">
        <p><strong style="color: #6BB76B;">Banking Customer Support AI</strong> | Powered by LangGraph</p>
        <p style="font-size: 12px; color: #999;">Confidential - For authorized use only</p>
    </div>
""", unsafe_allow_html=True)