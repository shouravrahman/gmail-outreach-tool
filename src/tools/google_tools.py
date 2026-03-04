import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

class GoogleTool:
    def __init__(self, credentials_dict):
        self.creds = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)

    def read_sheet(self, spreadsheet_id, range_name):
        sheet = self.sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheet_id=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            return []
        
        headers = values[0]
        leads = []
        for row in values[1:]:
            lead = {}
            for i, header in enumerate(headers):
                lead[header] = row[i] if i < len(row) else ''
            leads.append(lead)
        return leads

    def send_email(self, to, subject, body):
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            self.gmail_service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

def get_gmail_auth_url(client_config):
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = 'http://localhost:3001/api/auth/callback'
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url, flow

def finalize_auth(flow, authorization_response):
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    return json.loads(creds.to_json())
