from typing import TypedDict, List, Dict, Any, Optional
import json
import time
import random
import os
import logging

logger = logging.getLogger(__name__)

# Try to import LangChain components (optional)
try:
    from langgraph.graph import StateGraph, END  # type: ignore
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    from langchain_openai import ChatOpenAI  # type: ignore
    from langchain_ollama import ChatOllama  # type: ignore
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
    LANGCHAIN_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    LANGCHAIN_AVAILABLE = False
    logger.debug(f"LangChain not available: {type(e).__name__}")
    # Fallback classes if langchain not available
    StateGraph = None  # type: ignore
    ChatGoogleGenerativeAI = None  # type: ignore
    ChatOpenAI = None  # type: ignore
    ChatOllama = None  # type: ignore
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content

from src.tools.google_tools import GoogleTool
from src.tools.resend_tools import ResendTool
from src.utils.database import Session, Campaign, EmailLog, GoogleAccount, Draft, ResendAccount

class AgentState(TypedDict):
    campaign_id: int
    account_id: int
    leads: List[Dict[str, Any]]
    drafts: List[Dict[str, Any]]
    current_lead_index: int
    approved: bool
    status: str
    errors: List[str]

def get_llm(provider="gemini"):
    """Get LLM instance based on provider"""
    if not LANGCHAIN_AVAILABLE:
        logger.warning("LangChain not available - returning None")
        return None
    
    try:
        if provider == "gemini":
            if ChatGoogleGenerativeAI is None:
                return None
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GOOGLE_API_KEY"))
        elif provider == "ollama":
            if ChatOllama is None:
                return None
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return ChatOllama(model="llama3", base_url=base_url)
        else:
            # Default to OpenAI
            if ChatOpenAI is None:
                return None
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL")
            return ChatOpenAI(model=model, openai_api_key=api_key, base_url=base_url)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return None

def initialize_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    
    if not campaign:
        return {"status": "error", "errors": ["Campaign not found"]}
    
    # Get the correct tool for the provider
    leads = []
    try:
        # Convert column to string for comparison
        provider_str = str(campaign.outreach_provider) if campaign.outreach_provider else ''
        if provider_str == 'gmail':
            account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
            if account:
                tool = GoogleTool(account.credentials)
                sheet_id = campaign.sheet_url.split("/d/")[1].split("/")[0]
                leads = tool.read_sheet(sheet_id, "A:Z")
        else:
            # Assume Google Sheets as lead source even for Resend
            account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
            if account:
                tool = GoogleTool(account.credentials)
                sheet_id = campaign.sheet_url.split("/d/")[1].split("/")[0]
                leads = tool.read_sheet(sheet_id, "A:Z")
    except Exception as e:
        session.close()
        return {"status": "error", "errors": [f"Sheet error: {str(e)}"]}
    
    session.close()
    return {"leads": leads, "status": "drafting", "current_lead_index": 0}

def draft_messages_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    
    if not campaign:
        session.close()
        return {"status": "error", "errors": ["Campaign not found"]}
    
    # Convert column values to strings for proper typing
    provider_str = str(campaign.provider) if campaign.provider else "gemini"
    prompt_template = str(campaign.prompt_template) if campaign.prompt_template else ""
    
    llm = get_llm(provider_str)
    if not llm:
        session.close()
        return {"status": "error", "errors": ["LLM not available"]}
    
    batch_size = 5 # Small batch size for top-notch rate stability
    start_idx = state.get("current_lead_index", 0)
    end_idx = start_idx + batch_size
    leads_to_process = state["leads"][start_idx:end_idx]
    
    if not leads_to_process:
        session.close()
        return {"status": "awaiting_approval"}

    new_drafts = []
    for lead in leads_to_process:
        recipient_email = lead.get("Email") or lead.get("email")
        if not recipient_email:
            continue
            
        # Deduplication
        existing = session.query(Draft).filter(Draft.campaign_id == campaign.id, Draft.recipient_email == recipient_email).first()
        if existing:
            continue
            
        lead_str = json.dumps(lead)
        prompt = f"Using this lead data: {lead_str}\n\nDraft a personalized email based on this instruction: {prompt_template}"
        
        # Rate Limit Aware Invocation
        retries = 3
        while retries > 0:
            try:
                response = llm.invoke([
                    SystemMessage(content="You are an expert outreach copywriter. Return ONLY the JSON with 'subject' and 'body' keys."),
                    HumanMessage(content=prompt)
                ])
                break
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print(f"⚠️ Rate limit hit. Backing off... ({retries} retries left)")
                    time.sleep(30 * (4 - retries))
                    retries -= 1
                else:
                    raise e
        
        if retries == 0:
            print(f"❌ Failed to draft for {recipient_email} after retries.")
            continue

        try:
            content = json.loads(response.content)
            subj = content['subject']
            body = content['body']
        except:
            subj = f"Question for {lead.get('Name', 'you')}"
            body = response.content
            
        draft = Draft(
            campaign_id=campaign.id,
            recipient_email=recipient_email,
            recipient_name=lead.get("Name") or lead.get("name"),
            subject=subj,
            body=body,
            status='pending'
        )
        session.add(draft)
        new_drafts.append({"email": recipient_email, "subject": subj, "body": body})
            
    session.commit()
    session.close()
    
    new_index = end_idx
    if new_index >= len(state["leads"]):
        return {"drafts": new_drafts, "status": "awaiting_approval", "current_lead_index": new_index}
    else:
        return {"drafts": state["drafts"] + new_drafts, "status": "drafting_pause", "current_lead_index": new_index}

def wait_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    delay = campaign.settings.get("delay_seconds", 60)
    jitter = random.randint(-5, 5)
    time.sleep(max(1, delay + jitter))
    session.close()
    return state

def wait_draft_node(state: AgentState):
    # Short pause between drafting batches to respect API limits
    time.sleep(random.randint(5, 15))
    return state

def send_emails_node(state: AgentState):
    session = Session()
    try:
        campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
        if not campaign:
            return {"status": "error", "errors": ["Campaign not found during send."]}

        # Get a batch of approved drafts to send
        drafts_to_send = session.query(Draft).filter(
            Draft.campaign_id == campaign.id,
            Draft.status.in_(['approved', 'edited'])
        ).limit(5).all() # Process up to 5 emails per worker cycle

        if not drafts_to_send:
            # Check if there are any non-sent drafts left
            remaining_drafts = session.query(Draft).filter(Draft.campaign_id == campaign.id, Draft.status != 'sent').count()
            if remaining_drafts == 0:
                campaign.status = "completed" # type: ignore # Mark campaign as completed in DB
                session.commit()
                return {"status": "completed"}
            else:
                # Drafts exist but are not approved, wait for approval.
                return {"status": "awaiting_approval"}

        delay = campaign.settings.get("delay_seconds", 60)

        for draft in drafts_to_send:
            success = False
            try:
                provider_str = str(campaign.outreach_provider) if campaign.outreach_provider else ''

                if provider_str == 'gmail':
                    account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
                    if account:
                        tool = GoogleTool(account.credentials)
                        success = tool.send_email(str(draft.recipient_email), str(draft.subject or ""), str(draft.body or ""))
                elif provider_str == 'resend':
                    account = session.query(ResendAccount).filter(ResendAccount.id == campaign.outreach_account_id).first()
                    if account:
                        tool = ResendTool(account.api_key)
                        success = tool.send_email(str(account.from_email), str(draft.recipient_email), str(draft.subject or ""), str(draft.body or ""))

            except Exception as e:
                logger.error(f"Send error for draft {draft.id}: {e}")
                success = False

            if success:
                log = EmailLog(
                    campaign_id=str(campaign.id),
                    account_id=campaign.outreach_account_id,
                    recipient=str(draft.recipient_email),
                    subject=str(draft.subject or ""),
                    body=str(draft.body or ""),
                    status="sent"
                )
                session.add(log)
                draft.status = "sent" # type: ignore
            else:
                draft.status = "failed" # type: ignore

            session.commit() # Commit after each email attempt

            # Wait for the configured delay before the next email
            jitter = random.randint(-5, 5)
            time.sleep(max(1, delay + jitter))

        return {"status": "sending"}

    finally:
        session.close()

def create_workflow(checkpointer=None):
    if StateGraph is None:
        raise RuntimeError("LangGraph is not available. Please install it with 'pip install langgraph'")

    workflow = StateGraph(AgentState)
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("draft", draft_messages_node)
    workflow.add_node("wait_draft", wait_draft_node)
    workflow.add_node("wait", wait_node)
    workflow.add_node("send", send_emails_node)
    
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "draft")
    
    workflow.add_conditional_edges(
        "draft",
        lambda x: x["status"],
        {
            "drafting_pause": "wait_draft",
            "awaiting_approval": END,
            "error": END
        }
    )
    workflow.add_edge("wait_draft", "draft")
    
    workflow.add_conditional_edges(
        "send",
        lambda x: x["status"],
        {
            "sending": END, # A batch was sent, worker will re-invoke.
            "completed": END,
            "awaiting_approval": END, # No approved drafts, stop and wait.
            "error": END
        }
    )
    # The 'wait' node is no longer needed in the sending loop as the delay
    # is now handled within the 'send_emails_node' itself.
    
    return workflow.compile(checkpointer=checkpointer)
