import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)
from dotenv import load_dotenv
from src.utils.database import Session, GoogleAccount, Campaign, ResendAccount
from src.tools.google_tools import get_gmail_auth_url, finalize_auth
from src.utils.assistant import get_assistant_response, stop_campaign_by_name

load_dotenv()

# Conversation states for /campaign
CHOOSING_NAME, CHOOSING_SHEET, CHOOSING_PROMPT, CHOOSING_AI_MODEL, CHOOSING_OUTREACH_PROVIDER, CHOOSING_ACCOUNT = range(6)

# Dictionary for auth flows
auth_flows = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 <b>AI Outreach Agent Active</b>\n\n"
        "Commands:\n"
        "/connect - Link a Gmail account\n"
        "/connect_resend - Link a Resend domain\n"
        "/accounts - List all connected accounts\n"
        "/campaign - Start a campaign wizard\n"
        "/status - Quick status check\n"
        "/stop [name] - Stop a campaign\n\n"
        "💬 <b>Pro Tip:</b> You can just talk to me! Ask:\n"
        "<i>'How is the SaaS campaign doing?'</i>",
        parse_mode='HTML'
    )

# --- Account Management ---
async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client_json = os.getenv("GOOGLE_CLIENT_JSON")
    if not client_json:
        await update.message.reply_text("❌ `GOOGLE_CLIENT_JSON` not found in `.env`")
        return
    
    try:
        client_config = json.loads(client_json)
        auth_url, flow = get_gmail_auth_url(client_config)
        # Re-using the logic from finalize_auth. 
        # For simplicity in this demo, we store the flow.
        auth_flows[update.effective_user.id] = flow
        
        instructions = (
            "🔗 <b>Connect Gmail</b>\n\n"
            f'1. <a href="{auth_url}">Click here to authorize access</a>.\n'
            "2. Sign in with your Google account.\n"
            "3. <b>Important:</b> After authorizing, you will be redirected to a page that won't load (it starts with <i>localhost:3001</i>).\n"
            "4. <b>Copy the entire URL</b> from your browser's address bar and <b>paste it back here</b> to finish."
        )
        await update.message.reply_text(instructions, parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting up auth: {str(e)}")

async def connect_resend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 <b>Connect Resend</b>\n\n"
        "Please provide your API Key and the Email you want to send from in this format:\n"
        "<code>API_KEY | hello@yourdomain.com</code> (Use a vertical bar <code>|</code> to separate)",
        parse_mode='HTML'
    )

async def handle_resend_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "|" not in text:
        return False # Let other handlers take it
        
    try:
        api_key, from_email = [x.strip() for x in text.split("|")]
        domain = from_email.split("@")[1]
        
        session = Session()
        new_acc = ResendAccount(name=domain, from_email=from_email)
        new_acc.api_key = api_key
        session.add(new_acc)
        session.commit()
        session.close()
        
        await update.message.reply_text(f"✅ Linked Resend domain: <b>{domain}</b>", parse_mode='HTML')
        return True
    except Exception as e:
        await update.message.reply_text(f"❌ Error linking Resend: {str(e)}")
        return True

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    g_accs = session.query(GoogleAccount).all()
    r_accs = session.query(ResendAccount).all()
    session.close()
    
    await update.message.reply_text(text, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = get_assistant_response("Give me a brief status of all current campaigns.")
    await update.message.reply_text(response, parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /stop [campaign_name]")
        return
    name = " ".join(context.args)
    if stop_campaign_by_name(name):
        await update.message.reply_text(f"🛑 Campaign '{name}' stopped.")
    else:
        await update.message.reply_text(f"❌ Campaign '{name}' not found.")

# --- Campaign Wizard ---
async def campaign_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 <b>Step 1: Campaign Name</b>\nWhat should we call this outreach run?", parse_mode='HTML')
    return CHOOSING_NAME

async def campaign_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['campaign_name'] = update.message.text
    await update.message.reply_text("📊 <b>Step 2: Google Sheet URL</b>\nPaste the link to your spreadsheet.", parse_mode='HTML')
    return CHOOSING_SHEET

async def campaign_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['campaign_sheet'] = update.message.text
    await update.message.reply_text("✍️ <b>Step 3: AI Prompt</b>\nWhat should the AI do? (e.g. 'Invite them to my SaaS demo').", parse_mode='HTML')
    return CHOOSING_PROMPT

async def campaign_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['campaign_prompt'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Gemini (Cloud)", callback_data="gemini")],
        [InlineKeyboardButton("OpenAI (Cloud)", callback_data="openai")],
        [InlineKeyboardButton("Ollama (Local)", callback_data="ollama")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🤖 <b>Step 4: AI Model</b>\nWhich AI should draft these emails?", reply_markup=reply_markup, parse_mode='HTML')
    return CHOOSING_AI_MODEL

async def campaign_ai_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['ai_model'] = query.data
    
    keyboard = [
        [InlineKeyboardButton("Gmail (Personal/Workspace)", callback_data="gmail")],
        [InlineKeyboardButton("Resend (Custom Domain)", callback_data="resend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📨 <b>Step 5: Outreach Provider</b>\nHow should we send these emails?", reply_markup=reply_markup, parse_mode='HTML')
    return CHOOSING_OUTREACH_PROVIDER

async def campaign_outreach_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    outreach_provider = query.data
    context.user_data['outreach_provider'] = outreach_provider
    
    session = Session()
    if outreach_provider == 'gmail':
        accounts = session.query(GoogleAccount).all()
        keyboard = [[InlineKeyboardButton(acc.email, callback_data=str(acc.id))] for acc in accounts]
    else:
        accounts = session.query(ResendAccount).all()
        keyboard = [[InlineKeyboardButton(acc.name, callback_data=str(acc.id))] for acc in accounts]
    session.close()
    
    if not accounts:
        await query.edit_message_text(f"❌ No {outreach_provider} accounts linked. Use /connect first.", parse_mode='HTML')
        return ConversationHandler.END
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🔑 <b>Step 6: Select Account</b>\nWhich {outreach_provider} account?", reply_markup=reply_markup, parse_mode='HTML')
    return CHOOSING_ACCOUNT

async def campaign_finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    account_id = int(query.data)
    
    name = context.user_data['campaign_name']
    sheet = context.user_data['campaign_sheet']
    prompt = context.user_data['campaign_prompt']
    ai_model = context.user_data['ai_model']
    outreach_provider = context.user_data['outreach_provider']
    
    session = Session()
    new_campaign = Campaign(
        name=name,
        sheet_url=sheet,
        prompt_template=prompt,
        provider=ai_model,
        outreach_provider=outreach_provider,
        outreach_account_id=account_id,
        settings={"daily_limit": 50, "delay_seconds": 60}
    )
    session.add(new_campaign)
    session.commit()
    session.close()
    
    await query.edit_message_text(
        f"✅ <b>Campaign Created: {name}</b>\n\n"
        f"AI: {ai_model}\n"
        f"Sender: {outreach_provider} (ID: {account_id})\n\n"
        "Drafting will begin shortly. Edit & launch from your Dashboard!",
        parse_mode='HTML'
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Campaign creation cancelled.")
    return ConversationHandler.END

# --- Message Handler ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if it's a Resend link format
    if "|" in text:
        if await handle_resend_link(update, context):
            return

    # Check if it's a Google Auth code
    if user_id in auth_flows and ("code=" in text or len(text) > 40):
        flow = auth_flows.pop(user_id)
        try:
            creds = finalize_auth(flow, text)
            session = Session()
            new_acc = GoogleAccount(email=creds.get("email") or "Auth Account")
            new_acc.credentials = creds
            session.add(new_acc)
            session.commit()
            session.close()
            await update.message.reply_text("✅ Gmail Connected!")
            return
        except Exception as e:
            await update.message.reply_text(f"❌ Auth Error: {str(e)}")
            return

    # Default: Human-like AI assistant
    await update.message.reply_chat_action("typing")
    response = get_assistant_response(text)
    await update.message.reply_text(response, parse_mode='Markdown')

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    app = ApplicationBuilder().token(token).build()

    campaign_handler = ConversationHandler(
        entry_points=[CommandHandler('campaign', campaign_start)],
        states={
            CHOOSING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_name)],
            CHOOSING_SHEET: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_sheet)],
            CHOOSING_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, campaign_prompt)],
            CHOOSING_AI_MODEL: [CallbackQueryHandler(campaign_ai_model)],
            CHOOSING_OUTREACH_PROVIDER: [CallbackQueryHandler(campaign_outreach_provider)],
            CHOOSING_ACCOUNT: [CallbackQueryHandler(campaign_finalize)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("connect", connect_command))
    app.add_handler(CommandHandler("connect_resend", connect_resend))
    app.add_handler(CommandHandler("accounts", list_accounts))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(campaign_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
