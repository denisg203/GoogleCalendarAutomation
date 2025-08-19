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
    url = "https://api.football-data.org/v4/teams/65/matches?season=2025"
    headers = {"X-Auth-Token": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["matches"]

# Fetch all events in calendar
def fetch_calendar_events(service, calendar_id="primary"):
    events = []
    page_token = None
    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            pageToken=page_token,
            maxResults=2500,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events.extend(events_result.get("items", []))
        page_token = events_result.get("nextPageToken")
        if not page_token:
            break
    return events

# Force delete any existing Manchester City events
def clean_old_events(service, calendar_id="primary"):
    events = fetch_calendar_events(service, calendar_id)
    deleted_count = 0
    for e in events:
        summary = e.get("summary", "")
        description = e.get("description", "")
        extended_props = e.get("extendedProperties", {})
        if "Manchester City" in summary or "match_id:" in description or extended_props:
            try:
                service.events().delete(calendarId=calendar_id, eventId=e["id"]).execute()
                print(f"🗑️ Deleted old event: {summary}")
                deleted_count += 1
            except Exception as ex:
                print(f"⚠️ Error deleting {summary}: {ex}")
    print(f"\n✅ Deleted {deleted_count} old Manchester City events.")

# Add all matches fresh
def add_matches(service, matches, calendar_id="primary"):
    for m in matches:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        status = m["status"]

        if status == "CANCELLED":
            continue  # Skip canceled matches

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
            "description": f"match_id:{m['id']}"
        }

        try:
            service.events().insert(calendarId=calendar_id, body=event).execute()
            print(f"✅ Added: {title}")
        except HttpError as e:
            print(f"⚠️ Error adding {title}: {e}")

if __name__ == "__main__":
    service = google_calendar_service()
    print("Cleaning old events...")
    clean_old_events(service)
    print("Fetching matches...")
    matches = fetch_matches()
    print("Adding fresh matches...")
    add_matches(service, matches)
    print("\n🎉 Done! Your calendar should now show all Manchester City matches.")
