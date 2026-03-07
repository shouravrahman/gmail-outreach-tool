from typing import List, Dict, Any
import logging
from src.utils.database import Session, Campaign, EmailLog, Draft, GoogleAccount, ResendAccount
from src.agent.workflow import get_llm
import json

logger = logging.getLogger(__name__)

# Try to import LangChain message classes (optional)
try:
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
    LANGCHAIN_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    LANGCHAIN_AVAILABLE = False
    logger.debug(f"LangChain not available: {type(e).__name__}")
    # Fallback message classes if langchain not available
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content

def get_assistant_response(query: str) -> str:
    session = Session()
    campaigns = session.query(Campaign).all()
    accounts = session.query(GoogleAccount).all()
    resend_accounts = session.query(ResendAccount).all()
    
    # Prepare context for the LLM
    campaign_data = []
    for c in campaigns:
        sent_count = session.query(EmailLog).filter(EmailLog.campaign_id == c.id).count()
        draft_count = session.query(Draft).filter(Draft.campaign_id == c.id).count()
        campaign_data.append({
            "name": c.name,
            "status": c.status,
            "provider": c.provider,
            "outreach": c.outreach_provider,
            "sent": sent_count,
            "drafts": draft_count,
            "created_at": str(c.created_at)
        })
    
    account_summary = {
        "gmail_accounts": [a.email for a in accounts],
        "resend_domains": [a.name for a in resend_accounts]
    }
    
    context = f"""
    Current Campaigns: {json.dumps(campaign_data)}
    Connected Accounts: {json.dumps(account_summary)}
    """
    
    llm = get_llm("gemini") # Use Gemini for the assistant logic
    
    system_prompt = f"""
    You are the AI Outreach Assistant. Your job is to help the user manage their email campaigns.
    You have access to the following current state:
    {context}
    
    Answer the user's question concisely. If they ask to stop a campaign, explain that you can't do it directly yet but they can use the /stop command (upcoming).
    Be helpful and professional. Use Markdown for formatting.
    """
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        return response.content
    except Exception as e:
        return f"❌ Sorry, I couldn't process that: {str(e)}"
    finally:
        session.close()

def stop_campaign_by_name(name: str) -> bool:
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.name.ilike(f"%{name}%")).first()
    if campaign:
        campaign.status = 'stopped'
        session.commit()
        session.close()
        return True
    session.close()
    return False
