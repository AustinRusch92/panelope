import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.events',
]

# Paste the ID from: Panelope calendar -> Settings -> Integrate calendar
PANELOPE_CAL_ID = os.getenv("PANELOPE_CAL_ID")
TIMEZONE = 'America/New_York'


def get_service(api='gmail', version='v1'):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())
    return build(api, version, credentials=creds)


def create_event(title, start_iso, duration_min=20, confirm=True):
    """Create an event on the Panelope calendar ONLY. Create-only, no edit/delete."""
    start = datetime.fromisoformat(start_iso)
    end = start + timedelta(minutes=duration_min)

    if confirm:
        print(f"About to create: '{title}' at {start} for {duration_min} min")
        if input("Create it? (y/n): ").strip().lower() != 'y':
            return "Cancelled."

    service = get_service('calendar', 'v3')
    body = {
        'summary': title,
        'start': {'dateTime': start.isoformat(), 'timeZone': TIMEZONE},
        'end': {'dateTime': end.isoformat(), 'timeZone': TIMEZONE},
    }
    event = service.events().insert(calendarId=PANELOPE_CAL_ID, body=body).execute()
    return f"Created: {event.get('htmlLink')}"

def find_promo_candidates(service, max_results=50):
    query = "category:promotions in:inbox -from:linkedin.com -from:lensa.com -from:ziprecruiter.com"
    resp = service.users().messages().list(
        userId='me', q=query, maxResults=max_results
    ).execute()
    ids = [m['id'] for m in resp.get('messages', [])]

    candidates = []
    for mid in ids:
        msg = service.users().messages().get(
            userId='me', id=mid, format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        candidates.append({
            'id': mid,
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
        })
    return candidates


def archive_messages(service, message_ids):
    """Archive-only: removes the INBOX label. No delete, no trash, no send."""
    for mid in message_ids:
        service.users().messages().modify(
            userId='me', id=mid,
            body={'removeLabelIds': ['INBOX']}
        ).execute()


if __name__ == '__main__':
    service = get_service()
    candidates = find_promo_candidates(service)

    if not candidates:
        print("No promo candidates found.")
    else:
        for i, c in enumerate(candidates, 1):
            print(f"{i}. {c['from']} | {c['subject']}")
        print(f"\n{len(candidates)} candidates. Nothing archived yet.")

        answer = input("Archive all of these? (yes/no): ")
        if answer.strip().lower() == 'yes':
            archive_messages(service, [c['id'] for c in candidates])
            print("Archived.")
        else:
            print("Nothing archived.")
