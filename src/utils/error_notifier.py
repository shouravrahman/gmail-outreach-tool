"""
Telegram Error Notifier
Sends critical errors and alerts to a Telegram chat
Usage: Initialize once in app.py, then use notify_error() anywhere
"""

import os
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Send error notifications to Telegram"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id and TELEGRAM_AVAILABLE)
        
        if self.enabled:
            self.bot = Bot(token=self.bot_token)
            logger.info(f"✅ Telegram notifier enabled (Chat ID: {self.chat_id})")
        else:
            logger.warning("⚠️ Telegram notifier disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
    
    async def send_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        severity: str = "ERROR"  # ERROR, WARNING, INFO
    ):
        """
        Send error notification to Telegram
        
        Args:
            error_type: Type of error (e.g., "DatabaseError", "EmailFailed")
            message: Human-readable error message
            details: Additional context (dict)
            user_id: Affected user ID
            severity: ERROR, WARNING, or INFO
        """
        if not self.enabled:
            return
        
        try:
            # Format timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # Build message
            emoji = "🔴" if severity == "ERROR" else "🟡" if severity == "WARNING" else "🔵"
            
            text = f"""
{emoji} <b>{severity}: {error_type}</b>
<i>{timestamp}</i>

<b>Message:</b>
{message}
"""
            
            if user_id:
                text += f"\n<b>User:</b> <code>{user_id}</code>"
            
            if details:
                text += "\n\n<b>Details:</b>\n"
                text += "<pre>" + json.dumps(details, indent=2)[:500] + "</pre>"
            
            # Send to Telegram
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode='HTML'
            )
            logger.info(f"📱 Telegram alert sent: {error_type}")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
    
    def send_error_sync(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        severity: str = "ERROR"
    ):
        """Synchronous wrapper for send_error()"""
        if not self.enabled:
            return
        
        try:
            asyncio.run(self.send_error(error_type, message, details, user_id, severity))
        except RuntimeError:
            # Event loop already running (in Streamlit), use this instead:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.send_error(error_type, message, details, user_id, severity))
                else:
                    loop.run_until_complete(self.send_error(error_type, message, details, user_id, severity))
            except Exception as e:
                logger.error(f"Could not send async Telegram notification: {e}")


# Global instance
_notifier = None

def get_notifier() -> TelegramNotifier:
    """Get or create the global Telegram notifier"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier

def notify_error(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    severity: str = "ERROR"
):
    """
    Convenience function to send error notification
    
    Example:
        try:
            send_email(...)
        except Exception as e:
            notify_error(
                "EmailFailed",
                f"Failed to send email to {recipient}",
                {"error": str(e), "recipient": recipient},
                user_id=current_user.id
            )
    """
    notifier = get_notifier()
    notifier.send_error_sync(error_type, message, details, user_id, severity)

def notify_warning(message: str, **kwargs):
    """Convenience function for warnings"""
    notify_error("Warning", message, severity="WARNING", **kwargs)

def notify_info(message: str, **kwargs):
    """Convenience function for info messages"""
    notify_error("Info", message, severity="INFO", **kwargs)
