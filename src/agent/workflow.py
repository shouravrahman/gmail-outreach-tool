from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from src.tools.google_tools import GoogleTool
from src.tools.resend_tools import ResendTool
from src.utils.database import Session, Campaign, EmailLog, GoogleAccount, Draft, ResendAccount
import json
import time
import random

class AgentState(TypedDict):
    campaign_id: int
    account_id: int
    leads: List[Dict[str, Any]]
    drafts: List[Dict[str, Any]]
    approved: bool
    status: str
    errors: List[str]

import os

def get_llm(provider="gemini"):
    if provider == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GOOGLE_API_KEY"))
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model="llama3", base_url=base_url)
    else:
        # Default to OpenAI logic
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") # For OpenRouter etc.
        return ChatOpenAI(model=model, openai_api_key=api_key, base_url=base_url)

def initialize_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    
    if not campaign:
        return {"status": "error", "errors": ["Campaign not found"]}
    
    # Get the correct tool for the provider
    leads = []
    if campaign.outreach_provider == 'gmail':
        account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
        tool = GoogleTool(account.credentials)
        sheet_id = campaign.sheet_url.split("/d/")[1].split("/")[0]
        leads = tool.read_sheet(sheet_id, "A:Z")
    else:
        # For Resend, we still need a sheet to get leads
        # Typically we assume a Google Sheet even for Resend, or we'd need another lead source
        # Let's assume Google Sheets is the lead source for now
        account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
        if account:
            tool = GoogleTool(account.credentials)
            sheet_id = campaign.sheet_url.split("/d/")[1].split("/")[0]
            leads = tool.read_sheet(sheet_id, "A:Z")
    
    session.close()
    return {"leads": leads, "status": "drafting"}

def draft_messages_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    llm = get_llm(campaign.provider)
    prompt_template = campaign.prompt_template
    
    new_drafts = []
    for lead in state["leads"]:
        recipient_email = lead.get("Email") or lead.get("email")
        if not recipient_email:
            continue
            
        # Deduplication
        existing = session.query(Draft).filter(Draft.campaign_id == campaign.id, Draft.recipient_email == recipient_email).first()
        if existing:
            continue
            
        lead_str = json.dumps(lead)
        prompt = f"Using this lead data: {lead_str}\n\nDraft a personalized email based on this instruction: {prompt_template}"
        response = llm.invoke([
            SystemMessage(content="You are an expert outreach copywriter. Return ONLY the JSON with 'subject' and 'body' keys."),
            HumanMessage(content=prompt)
        ])
        
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
    return {"drafts": new_drafts, "status": "awaiting_approval"}

def send_emails_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    
    # Get the next "approved" or "edited" draft
    draft = session.query(Draft).filter(Draft.campaign_id == campaign.id, Draft.status.in_(['approved', 'edited'])).first()
    
    if not draft:
        session.close()
        return {"status": "completed"}
        
    success = False
    if campaign.outreach_provider == 'gmail':
        account = session.query(GoogleAccount).filter(GoogleAccount.id == campaign.outreach_account_id).first()
        if account:
            tool = GoogleTool(account.credentials)
            success = tool.send_email(draft.recipient_email, draft.subject, draft.body)
    elif campaign.outreach_provider == 'resend':
        account = session.query(ResendAccount).filter(ResendAccount.id == campaign.outreach_account_id).first()
        api_key = account.api_key if account else os.getenv("RESEND_API_KEY")
        from_email = account.from_email if account else os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
        
        if api_key:
            tool = ResendTool(api_key)
            success = tool.send_email(from_email, draft.recipient_email, draft.subject, draft.body)
        
    if success:
        log = EmailLog(
            campaign_id=campaign.id,
            account_id=campaign.outreach_account_id,
            recipient=draft.recipient_email,
            subject=draft.subject,
            body=draft.body,
            status="sent"
        )
        session.add(log)
        draft.status = 'sent'
    else:
        draft.status = 'failed'
    
    session.commit()
    session.close()
    
    # We return "sending" to trigger the loop in the graph
    return {"status": "sending"}

def wait_node(state: AgentState):
    session = Session()
    campaign = session.query(Campaign).filter(Campaign.id == state["campaign_id"]).first()
    # Simple delay to respect rate limits / human simulation
    delay = campaign.settings.get("delay_seconds", 60)
    jitter = random.randint(-10, 10)
    time.sleep(max(1, delay + jitter))
    session.close()
    return state

def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("draft", draft_messages_node)
    workflow.add_node("wait", wait_node)
    workflow.add_node("send", send_emails_node)
    
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "draft")
    workflow.add_edge("draft", END) # Hold for UI/Telegram approval
    
    workflow.add_conditional_edges(
        "send",
        lambda x: x["status"],
        {
            "sending": "wait",
            "completed": END
        }
    )
    workflow.add_edge("wait", "send") # Loop back to send next
    
    return workflow.compile()
