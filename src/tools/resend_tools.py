import os
import requests
from typing import Optional

class ResendTool:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.resend.com"

    def send_email(self, from_email: str, to: str, subject: str, body: str) -> bool:
        """
        Sends an email using the Resend API.
        """
        url = f"{self.base_url}/emails"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": body # Resend expects HTML or Text
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200 or response.status_code == 201:
                return True
            else:
                print(f"Resend error: {response.text}")
                return False
        except Exception as e:
            print(f"Error sending email via Resend: {e}")
            return False
