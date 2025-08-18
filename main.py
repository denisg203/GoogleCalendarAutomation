from __future__ import print_function
import datetime
import requests
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Calendar API setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def google_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

# Fetch Manchester City matches from football-data.org
def fetch_matches():
    url = "https://api.football-data.org/v4/teams/65/matches?season=2025"  # 65 = Man City
    headers = {"X-Auth-Token": "***REMOVED***"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["matches"]

# Get existing events from Google Calendar (only ones created by this sync, i.e., with numeric IDs)
def fetch_calendar_events(service, calendar_id="primary"):
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

# Sync football-data matches into Google Calendar
def sync_matches(service, matches, calendar_id="primary"):
    # Build a dict of match_id -> match data
    match_map = {str(m["id"]): m for m in matches}

    # Get existing events
    events = fetch_calendar_events(service, calendar_id)
    # Map match_id to actual Google Calendar event ID
    existing_event_map = {}
    for e in events:
        # Only consider events we created (optional: you can check a prefix in summary)
        summary = e.get("summary", "")
        for m_id, m in match_map.items():
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            if f"{home} vs {away}" in summary:
                existing_event_map[m_id] = e["id"]
                break

    # Step 1: Add or update matches
    for match_id, m in match_map.items():
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        status = m["status"]

        if status == "CANCELLED":
            # Delete if exists
            if match_id in existing_event_map:
                try:
                    service.events().delete(calendarId=calendar_id, eventId=existing_event_map[match_id]).execute()
                    print(f"🗑️ Deleted (cancelled): {home} vs {away}")
                except Exception as e:
                    print(f"⚠️ Error deleting {home} vs {away}: {e}")
            continue

        # Build event
        start_dt = datetime.datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        end_dt = start_dt + datetime.timedelta(hours=2)
        title = f"{home} vs {away}"
        if status == "POSTPONED":
            title = "[POSTPONED] " + title

        event = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/London"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/London"},
            "colorId": "7",
        }

        try:
            if match_id in existing_event_map:
                # Update existing event
                service.events().update(
                    calendarId=calendar_id,
                    eventId=existing_event_map[match_id],
                    body=event
                ).execute()
                print(f"🔄 Updated: {title}")
            else:
                # Insert new event (let Google assign ID)
                service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"✅ Added: {title}")
        except HttpError as e:
            print(f"⚠️ Error syncing {title}: {e}")

    # Step 2: Remove stale events (in calendar but not in football-data)
    stale_ids = set(existing_event_map.keys()) - set(match_map.keys())
    for stale_id in stale_ids:
        try:
            service.events().delete(calendarId=calendar_id, eventId=existing_event_map[stale_id]).execute()
            print(f"🗑️ Deleted stale event with ID {stale_id}")
        except Exception as e:
            print(f"⚠️ Error deleting stale event {stale_id}: {e}")

if __name__ == "__main__":
    service = google_calendar_service()
    matches = fetch_matches()
    sync_matches(service, matches)
