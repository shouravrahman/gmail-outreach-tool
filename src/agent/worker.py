import time
import signal
import sys
from src.utils.database import Session, Campaign
from src.agent.workflow import create_workflow

# Try to import checkpointer
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    MemorySaver = None

def run_worker():
    print("🚀 AI Outreach Worker Started...")
    checkpointer = MemorySaver() if MemorySaver else None
    workflow = create_workflow(checkpointer=checkpointer)
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping worker...")
        sys.exit(0)
    
    try:
        signal.signal(signal.SIGINT, signal_handler)
    except ValueError:
        pass  # Ignore if running in a background thread
    
    while True:
        session = Session()
        # Find campaigns that are in 'sending' or 'drafting' status
        active_campaigns = session.query(Campaign).filter(Campaign.status.in_(['sending', 'drafting'])).all()
        
        for campaign in active_campaigns:
            print(f"🔄 Processing Campaign: {campaign.name} (Status: {campaign.status})")
            
            # Prepare state for LangGraph
            initial_state = {
                "campaign_id": campaign.id,
                "account_id": campaign.outreach_account_id,
                "leads": [],
                "drafts": [],
                "approved": False,
                "status": campaign.status,
                "errors": []
            }
            
            try:
                # Run the workflow
                # The workflow will update the database (Drafts,Logs) directly
                config = {"configurable": {"thread_id": str(campaign.id)}}
                result = workflow.invoke(initial_state, config=config)
                
                # If the workflow finishes a cycle, we update the status based on output
                if result.get("status") == "completed":
                    campaign.status = "completed" # type: ignore
                    print(f"✅ Campaign {campaign.name} completed.")
                
            except Exception as e:
                print(f"❌ Error in worker for campaign {campaign.name}: {e}")
                campaign.status = "error" # type: ignore
            
            session.commit()
            
        session.close()
        time.sleep(10) # Poll every 10 seconds

if __name__ == "__main__":
    run_worker()
