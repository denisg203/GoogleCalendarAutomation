import datetime
import requests
import json
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# Google Calendar API setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def google_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS environment variable")
    creds_info = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

# Fetch Manchester City matches from football-data.org
def fetch_matches():
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("Missing FOOTBALL_DATA_API_KEY environment variable")
    url = "https://api.football-data.org/v4/teams/65/matches?season=2025"  # 65 = Man City
    headers = {"X-Auth-Token": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["matches"]

# Get existing events from Google Calendar
def fetch_calendar_events(service, calendar_id="primary"):
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

# Sync matches into Google Calendar
def sync_matches(service, matches, calendar_id="primary"):
    match_map = {str(m["id"]): m for m in matches}

    # Fetch existing events
    events = fetch_calendar_events(service, calendar_id)

    # Build map: match_id -> event_id (from description)
    existing_event_map = {}
    for e in events:
        desc = e.get("description", "")
        if desc.startswith("match_id:"):
            m_id = desc.split("match_id:")[-1].strip()
            existing_event_map[m_id] = e["id"]

    for match_id, m in match_map.items():
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        status = m["status"]

        if status == "CANCELLED":
            if match_id in existing_event_map:
                try:
                    service.events().delete(calendarId=calendar_id, eventId=existing_event_map[match_id]).execute()
                    print(f"🗑️ Deleted (cancelled): {home} vs {away}")
                except Exception as e:
                    print(f"⚠️ Error deleting {home} vs {away}: {e}")
            continue

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
            "description": f"match_id:{match_id}"
        }

        try:
            if match_id in existing_event_map:
                service.events().update(
                    calendarId=calendar_id,
                    eventId=existing_event_map[match_id],
                    body=event
                ).execute()
                print(f"🔄 Updated: {title}")
            else:
                service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"✅ Added: {title}")
        except HttpError as e:
            print(f"⚠️ Error syncing {title}: {e}")

    # Remove stale events (exist in calendar but not in API)
    stale_ids = set(existing_event_map.keys()) - set(match_map.keys())
    for stale_id in stale_ids:
        try:
            service.events().delete(calendarId=calendar_id, eventId=existing_event_map[stale_id]).execute()
            print(f"🗑️ Deleted stale event with match_id {stale_id}")
        except Exception as e:
            print(f"⚠️ Error deleting stale event {stale_id}: {e}")

if __name__ == "__main__":
    service = google_calendar_service()
    matches = fetch_matches()
    sync_matches(service, matches)
