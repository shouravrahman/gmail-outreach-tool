import streamlit as st
import pandas as pd
import sys
import os

# Ensure the project root is in original path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.database import Session, Campaign, EmailLog, GoogleAccount, Draft, ResendAccount
from sqlalchemy import desc

# Page Config
st.set_page_config(
    page_title="Bulk Email AI Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Glassmorphism Effect for Cards */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* Custom Header Styling */
    h1 {
        font-weight: 800;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem !important;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }

    /* Responsive Data Editor */
    [data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Sidebar Polish */
    section[data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Bulk Email AI Agent")

# Sidebar for stats
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/rocket.png", width=80)
    st.title("Admin Panel")
    st.markdown("---")
    
    session = Session()
    total_google = session.query(GoogleAccount).count()
    total_resend = session.query(ResendAccount).count()
    total_campaigns = session.query(Campaign).count()
    total_sent = session.query(EmailLog).filter(EmailLog.status == 'sent').count()
    total_failed = session.query(EmailLog).filter(EmailLog.status == 'failed').count()
    
    st.metric("Gmail Accounts", total_google)
    st.metric("Resend Domains", total_resend)
    st.metric("Total Campaigns", total_campaigns)
    
    st.divider()
    st.subheader("Performance")
    st.metric("Sent Emails", total_sent, help="Total emails successfully delivered.")
    st.metric("Failed Emails", total_failed, delta_color="inverse", help="Check logs for errors.")
    session.close()

# Main Dashboard
col1, col2 = st.columns([1.2, 2.8], gap="large")

with col1:
    st.subheader("📋 Active Campaigns")
    session = Session()
    campaigns = session.query(Campaign).order_by(desc(Campaign.created_at)).all()
    
    if campaigns:
        for c in campaigns:
            status_color = "🟢" if c.status == 'sending' else "🟡" if c.status == 'drafting' else "⚪"
            with st.expander(f"{status_color} {c.name}", expanded=(c.status == 'sending')):
                st.caption(f"ID: {c.id} | Provider: **{c.outreach_provider.upper()}**")
                st.markdown(f"**Source:** [Google Sheet]({c.sheet_url})")
                
                # Control logic in a compact grid
                ctrl_col1, ctrl_col2 = st.columns(2)
                
                with ctrl_col1:
                    if c.status in ['pending', 'completed', 'stopped', 'error']:
                        if st.button(f"Start", key=f"launch_{c.id}", use_container_width=True, type="primary"):
                            c.status = 'sending'
                            session.commit()
                            st.toast(f"Starting {c.name}...", icon="🚀")
                            st.rerun()
                    elif c.status == 'sending':
                        if st.button(f"Pause", key=f"pause_{c.id}", use_container_width=True):
                            c.status = 'stopped'
                            session.commit()
                            st.toast("Campaign paused.")
                            st.rerun()

                with ctrl_col2:
                    if st.button(f"Redraft", key=f"redraft_{c.id}", use_container_width=True):
                        c.status = 'drafting'
                        session.commit()
                        st.toast("Regenerating drafts...")
                        st.rerun()
                
                if st.button(f"Delete Campaign", key=f"del_{c.id}", use_container_width=True, type="secondary"):
                    session.delete(c)
                    session.commit()
                    st.success("Deleted!")
                    st.rerun()
    else:
        st.info("No campaigns found. Use the Telegram bot to create one!")
    session.close()

    st.markdown("---")
    st.subheader("🛠️ Quick Help")
    with st.expander("Pro Tips"):
        st.markdown("""
        - **Gmail**: Best for personal, high-touch follow-ups.
        - **Resend**: Best for cold outreach at scale.
        - **Approval**: AI drafts emails first. You **must** approve them in the Editor tab before they send.
        """)

with col2:
    tab1, tab2 = st.tabs(["📝 Draft Editor", "📊 Email Activity Logs"])
    
    with tab1:
        session = Session()
        campaign_names = {c.id: c.name for c in session.query(Campaign).all()}
        
        if campaign_names:
            st.markdown("### Refine & Approve Drafts")
            selected_campaign_id = st.selectbox("Select Campaign", options=list(campaign_names.keys()), format_func=lambda x: campaign_names[x])
            
            drafts = session.query(Draft).filter(Draft.campaign_id == selected_campaign_id, Draft.status != 'sent').all()
            
            if drafts:
                st.info(f"⚡ **{len(drafts)}** drafts ready for review.")
                draft_data = []
                for d in drafts:
                    draft_data.append({
                        "ID": d.id,
                        "Recipient": d.recipient_email,
                        "Subject": d.subject,
                        "Body": d.body,
                        "Status": d.status
                    })
                
                df = pd.DataFrame(draft_data)
                edited_df = st.data_editor(df, num_rows="dynamic", key="draft_editor", hide_index=True, use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("💾 Save Edits", use_container_width=True):
                        for index, row in edited_df.iterrows():
                            d = session.query(Draft).filter(Draft.id == row['ID']).first()
                            if d:
                                d.subject = row['Subject']
                                d.body = row['Body']
                                if d.status == 'pending': d.status = 'edited'
                        session.commit()
                        st.success("Drafts updated!")
                
                with btn_col2:
                    if st.button("✅ Bulk Approve", use_container_width=True, type="primary"):
                        for d in drafts:
                            if d.status != 'sent': d.status = 'approved'
                        session.commit()
                        st.balloons()
                        st.success("All drafts approved for sending!")
                
                with btn_col3:
                    if st.button("🗑️ Wipe Drafts", use_container_width=True):
                        session.query(Draft).filter(Draft.campaign_id == selected_campaign_id).delete()
                        session.commit()
                        st.warning("All drafts cleared.")
                        st.rerun()
            else:
                st.info("No drafts found. AI might be working, or all are sent.")
        else:
            st.warning("Create your first campaign in Telegram.")
        session.close()

    with tab2:
        st.markdown("### Transmission Logs")
        session = Session()
        logs = session.query(EmailLog).order_by(desc(EmailLog.sent_at)).limit(50).all()
        if logs:
            log_data = []
            for l in logs:
                log_data.append({
                    "Time": l.sent_at.strftime("%H:%M:%S"),
                    "Recipient": l.recipient,
                    "Subject": l.subject,
                    "Status": "✅ Sent" if l.status == 'sent' else "❌ Failed"
                })
            st.table(pd.DataFrame(log_data))
        else:
            st.info("No logs generated yet. Hit 'Start' on a campaign!")
        session.close()

# Fixed bottom toolbar for refresh
st.markdown("---")
if st.button("🔄 Force Refresh Data", use_container_width=True):
    st.rerun()
