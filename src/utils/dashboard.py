"""
Streamlit Web Dashboard for Bulk Email Tool
Complete UI for email campaign management with authentication, monitoring, and controls
"""

import streamlit as st
import pandas as pd
try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    st.error("The 'plotly' library is missing. Please ensure it is installed and listed in requirements.txt.")
    st.stop()
from datetime import datetime, timedelta
import json
import logging
from typing import Optional, Dict, List, Any
import threading
import os
import sys

# --- PATH FIX START ---
# Ensure the project root is in sys.path so absolute imports (from src...) work
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.append(root_dir)
# --- PATH FIX END ---

# Import from src
from src.utils.security import (
    TokenManager, AccessControl, AuditLogger, SecretsManager, InputValidator
)
from src.utils.database import (
    create_user as db_create_user, get_user_by_email as db_get_user_by_email,
    update_user_last_login as db_update_user_last_login, create_campaign as db_create_campaign,
    get_user_campaigns as db_get_user_campaigns, approve_campaign as db_approve_campaign,
    get_campaign_stats as db_get_campaign_stats, get_audit_logs as db_get_audit_logs
)
from src.utils.error_notifier import notify_error
from src.agent.nlu_engine import get_nlu_engine
from src.agent.worker import run_worker
from src.utils.telegram_bot import main as run_bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIGURATION & THEME
# ============================================================================

st.set_page_config(
    page_title="Bulk Email Tool",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        color: #1f77b4;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0.25rem;
        font-weight: bold;
        margin: 0.25rem;
    }
    .status-success { background-color: #d4edda; color: #155724; }
    .status-warning { background-color: #fff3cd; color: #856404; }
    .status-danger { background-color: #f8d7da; color: #721c24; }
    .status-info { background-color: #d1ecf1; color: #0c5460; }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.token = None
    st.session_state.user_role = None
    st.session_state.authenticated = False
    st.session_state.nlu = get_nlu_engine()

# ============================================================================
# BACKGROUND SERVICES (FOR FREE HOSTING)
# ============================================================================

@st.cache_resource
def start_background_services():
    """Start Worker and Bot in background threads (Monolithic Mode)"""
    # Start AI Worker
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    
    # Start Telegram Bot
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return True

# ============================================================================
# AUTHENTICATION FUNCTIONS
# ============================================================================

def login_user(email: str, password: str) -> bool:
    """Authenticate user"""
    try:
        user = db_get_user_by_email(email)
        
        if not user:
            st.error("User not found")
            notify_error("LoginFailed", f"User not found: {email}", severity="WARNING")
            return False
        
        # Verify password
        secrets_mgr = SecretsManager()
        if not secrets_mgr.verify_password(password, user['password_hash'], user['password_salt']):
            st.error("Invalid password")
            notify_error("LoginFailed", f"Invalid password for: {email}", severity="WARNING")
            return False
        
        # Generate token
        token_mgr = TokenManager()
        token = token_mgr.generate_token(user['id'])
        
        # Update session
        st.session_state.user_id = user['id']
        st.session_state.token = token
        st.session_state.user_role = user['role']
        st.session_state.authenticated = True
        
        # Log login
        db_update_user_last_login(user['id'])
        
        st.success(f"Welcome back, {email}!")
        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        notify_error(
            "LoginError",
            f"Unexpected login error for {email}",
            details={"error": str(e)},
            severity="ERROR"
        )
        st.error("Login failed. Please try again.")
        return False

def register_user(email: str, password: str, name: str) -> bool:
    """Register new user"""
    try:
        # Validate inputs
        if not InputValidator.validate_email(email):
            st.error("Invalid email format")
            return False
        
        if len(password) < 8:
            st.error("Password must be at least 8 characters")
            return False
        
        # Check if user exists
        existing = db_get_user_by_email(email)
        if existing:
            st.error("Email already registered")
            return False
        
        # Hash password and create user
        secrets_mgr = SecretsManager()
        password_hash, salt = secrets_mgr.hash_password(password)
        
        import uuid
        user_id = str(uuid.uuid4())
        
        if db_create_user(user_id, email, password_hash, salt):
            st.success("Registration successful! Please log in.")
            return True
        else:
            st.error("Registration failed")
            return False
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        st.error("Registration failed. Please try again.")
        return False

def logout_user():
    """Logout user"""
    st.session_state.user_id = None
    st.session_state.token = None
    st.session_state.user_role = None
    st.session_state.authenticated = False
    st.success("Logged out successfully")
    st.rerun()

# ============================================================================
# LOGIN/REGISTER PAGE
# ============================================================================

def show_login_page():
    """Display login/register page"""
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🔐 Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn", use_container_width=True):
            if email and password:
                login_user(email, password)
            else:
                st.error("Please fill in all fields")
    
    with col2:
        st.markdown("### 📝 Register")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_name = st.text_input("Full Name", key="reg_name")
        
        if st.button("Register", key="register_btn", use_container_width=True):
            if reg_email and reg_password and reg_name:
                register_user(reg_email, reg_password, reg_name)
            else:
                st.error("Please fill in all fields")

# ============================================================================
# DASHBOARD PAGES
# ============================================================================

def dashboard_page():
    """Main dashboard with analytics"""
    st.markdown("# 📊 Dashboard")
    
    # Get user's campaigns
    campaigns = db_get_user_campaigns(st.session_state.user_id, limit=100)
    
    if not campaigns:
        st.info("No campaigns yet. Create your first campaign!")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Campaigns", len(campaigns))
    with col2:
        pending = sum(1 for c in campaigns if c['status'] == 'draft')
        st.metric("Pending Approval", pending)
    with col3:
        approved = sum(1 for c in campaigns if c['status'] == 'approved')
        st.metric("Approved", approved)
    with col4:
        completed = sum(1 for c in campaigns if c['status'] == 'completed')
        st.metric("Completed", completed)
    
    st.divider()
    
    # Campaign status chart
    status_counts = pd.DataFrame([
        {'Status': c['status'].upper(), 'Count': 1}
        for c in campaigns
    ]).groupby('Status').size().reset_index(name='Count')
    
    if not status_counts.empty:
        fig = px.pie(status_counts, values='Count', names='Status', title="Campaign Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent campaigns
    st.subheader("Recent Campaigns")
    campaigns_df = pd.DataFrame(campaigns).head(10)
    st.dataframe(campaigns_df, use_container_width=True, hide_index=True)

def campaigns_page():
    """Campaign management page"""
    st.markdown("# 📧 Campaigns")
    
    tab1, tab2, tab3 = st.tabs(["Create", "My Campaigns", "Approvals"])
    
    with tab1:
        st.markdown("### Create New Campaign")
        
        with st.form("campaign_form"):
            name = st.text_input("Campaign Name", max_chars=100)
            subject = st.text_input("Email Subject", max_chars=200)
            
            col1, col2 = st.columns(2)
            with col1:
                template_id = st.selectbox("Template (Optional)", ["None", "Template 1", "Template 2"])
            with col2:
                requires_approval = st.checkbox("Requires Approval", value=True)
            
            recipients_input = st.text_area(
                "Recipients (one email per line)",
                placeholder="email1@example.com\nemail2@example.com\n..."
            )
            
            submitted = st.form_submit_button("Create Campaign", use_container_width=True)
            
            if submitted:
                if not name or not subject or not recipients_input:
                    st.error("Please fill in all required fields")
                else:
                    recipients = [e.strip() for e in recipients_input.split('\n') if e.strip()]
                    
                    # Validate emails
                    is_valid, error = InputValidator.validate_emails_list(recipients)
                    if not is_valid:
                        st.error(f"Email validation error: {error}")
                    else:
                        campaign_data = {
                            'name': name,
                            'subject': subject,
                            'template_id': None if template_id == "None" else template_id,
                            'status': 'draft',
                            'requires_approval': requires_approval
                        }
                        
                        try:
                            campaign_id = db_create_campaign(campaign_data)
                            
                            # Log action
                            audit = AuditLogger()
                            audit.log_action(
                                user_id=st.session_state.user_id,
                                action='create_campaign',
                                resource='campaign',
                                status='success',
                                details={'campaign_id': campaign_id}
                            )
                            
                            st.success(f"Campaign created! ID: {campaign_id}")
                        except Exception as e:
                            logger.error(f"Campaign creation failed: {e}")
                            st.error("Failed to create campaign")
    
    with tab2:
        st.markdown("### My Campaigns")
        
        campaigns = db_get_user_campaigns(st.session_state.user_id, limit=100)
        
        if not campaigns:
            st.info("No campaigns yet")
        else:
            for campaign in campaigns:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.subheader(campaign['name'])
                with col2:
                    status = campaign['status']
                    if status == 'draft':
                        st.warning("DRAFT")
                    elif status == 'approved':
                        st.success("APPROVED")
                    else:
                        st.info(status.upper())
                with col3:
                    if st.button("View", key=f"view_{campaign['id']}", use_container_width=True):
                        st.session_state.selected_campaign = campaign['id']
                with col4:
                    if st.button("Delete", key=f"delete_{campaign['id']}", use_container_width=True):
                        st.warning("Delete feature coming soon")
    
    with tab3:
        st.markdown("### Pending Approvals")
        
        if st.session_state.user_role in ['admin', 'manager']:
            campaigns = db_get_user_campaigns(st.session_state.user_id, limit=100)
            pending = [c for c in campaigns if c['status'] == 'draft']
            
            if not pending:
                st.success("No pending approvals!")
            else:
                for campaign in pending:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.write(f"**{campaign['name']}**")
                    with col2:
                        if st.button("Approve", key=f"approve_{campaign['id']}", use_container_width=True):
                            db_approve_campaign(campaign['id'], st.session_state.user_id)
                            st.success("Campaign approved!")
                            st.rerun()
                    with col3:
                        if st.button("Reject", key=f"reject_{campaign['id']}", use_container_width=True):
                            st.info("Reject feature coming soon")
        else:
            st.warning("You don't have permission to approve campaigns")

def templates_page():
    """Email templates management"""
    st.markdown("# 🎨 Email Templates")
    
    tab1, tab2 = st.tabs(["Create", "My Templates"])
    
    with tab1:
        st.markdown("### Create New Template")
        
        with st.form("template_form"):
            name = st.text_input("Template Name", max_chars=100)
            subject = st.text_input("Email Subject", max_chars=200)
            html_content = st.text_area("HTML Content", height=300)
            variables_input = st.text_input(
                "Variables (comma-separated, e.g., {{name}}, {{company}})",
                placeholder="{{name}}, {{company}}, {{email}}"
            )
            
            submitted = st.form_submit_button("Create Template", use_container_width=True)
            
            if submitted:
                if not name or not subject or not html_content:
                    st.error("Please fill in required fields")
                else:
                    variables = [v.strip() for v in variables_input.split(',')] if variables_input else []
                    st.success(f"Template '{name}' created successfully!")
    
    with tab2:
        st.markdown("### My Templates")
        st.info("No templates yet. Create your first template!")

def analytics_page():
    """Detailed analytics page"""
    st.markdown("# 📈 Analytics")
    
    campaigns = db_get_user_campaigns(st.session_state.user_id, limit=100)
    
    if not campaigns:
        st.info("No data to display")
        return
    
    # Time range selector
    col1, col2 = st.columns(2)
    with col1:
        days = st.slider("Days", 1, 90, 30)
    
    # Overall statistics
    st.markdown("### Overall Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Campaigns", len(campaigns))
    with col2:
        st.metric("Total Recipients", sum(1 for c in campaigns for _ in [1]))
    with col3:
        st.metric("Total Sent", "Calculate from logs")
    with col4:
        st.metric("Open Rate", "N/A")
    
    st.divider()
    
    # Campaign performance table
    st.markdown("### Campaign Performance")
    
    perf_data = []
    for campaign in campaigns:
        stats = db_get_campaign_stats(campaign['id'])
        perf_data.append({
            'Campaign': campaign['name'],
            'Status': campaign['status'].upper(),
            'Total': stats.get('total', 0),
            'Sent': stats.get('sent', 0),
            'Failed': stats.get('failed', 0),
            'Opened': stats.get('opened', 0),
        })
    
    if perf_data:
        df = pd.DataFrame(perf_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

def settings_page():
    """User settings page"""
    st.markdown("# ⚙️ Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Account Settings")
        st.write(f"**User ID:** {st.session_state.user_id}")
        st.write(f"**Role:** {st.session_state.user_role}")
        
        if st.button("Logout", use_container_width=True, key="logout_btn"):
            logout_user()
    
    with col2:
        st.markdown("### Preferences")
        notifications = st.checkbox("Email Notifications", value=True)
        dark_mode = st.checkbox("Dark Mode", value=False)
        
        if st.button("Save Preferences", use_container_width=True):
            st.success("Preferences saved!")

def natural_language_page():
    """Natural language query interface"""
    st.markdown("# 💬 Natural Language Commands")
    
    st.markdown("""
    Use natural language to control your campaigns:
    - "Send emails to all gmail users"
    - "Show me campaigns from last week"
    - "Approve all pending campaigns"
    - "Filter recipients by domain"
    """)
    
    nlu = st.session_state.nlu
    
    query = st.text_input(
        "Enter your command:",
        placeholder="e.g., 'Send campaign to john@example.com and jane@example.com'"
    )
    
    if query:
        # Validate query safety
        is_safe, error = nlu.validate_query_safety(query)
        if not is_safe:
            st.error(f"Invalid query: {error}")
        else:
            # Process query
            intent, entities, confidence = nlu.process_query(query)
            
            st.markdown("### Query Analysis")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Intent", intent)
            with col2:
                st.metric("Confidence", f"{confidence:.0%}")
            with col3:
                st.metric("Entities Found", len(entities))
            
            if entities:
                st.markdown("### Detected Entities")
                entities_df = pd.DataFrame(entities)
                st.dataframe(entities_df, use_container_width=True, hide_index=True)
            
            if confidence > 0.6:
                st.success("✅ Command understood. Ready to execute.")
                if st.button("Execute Command", use_container_width=True):
                    st.info(f"Executing: {intent}")
                    # Execute command based on intent
            else:
                st.warning("⚠️ Low confidence. Please clarify your request.")

def audit_logs_page():
    """Audit logs viewer"""
    st.markdown("# 📋 Audit Logs")
    
    if st.session_state.user_role not in ['admin', 'manager']:
        st.warning("You don't have permission to view audit logs")
        return
    
    logs = db_get_audit_logs(user_id=st.session_state.user_id, limit=100)
    
    if not logs:
        st.info("No audit logs yet")
    else:
        logs_df = pd.DataFrame(logs)
        st.dataframe(logs_df, use_container_width=True, hide_index=True)

def main():
    """Main app"""
    # Start background services once
    start_background_services()

    if not st.session_state.authenticated:
        st.markdown("# 📧 Bulk Email Tool")
        show_login_page()
    else:
        # Sidebar navigation
        with st.sidebar:
            st.markdown(f"### Welcome, {st.session_state.user_role.upper()}")
            st.divider()
            
            page = st.radio(
                "Navigation",
                ["Dashboard", "Campaigns", "Templates", "Analytics", "Natural Language", "Audit Logs", "Settings"],
                label_visibility="collapsed"
            )
        
        # Page routing
        if page == "Dashboard":
            dashboard_page()
        elif page == "Campaigns":
            campaigns_page()
        elif page == "Templates":
            templates_page()
        elif page == "Analytics":
            analytics_page()
        elif page == "Natural Language":
            natural_language_page()
        elif page == "Audit Logs":
            audit_logs_page()
        elif page == "Settings":
            settings_page()

if __name__ == "__main__":
    main()