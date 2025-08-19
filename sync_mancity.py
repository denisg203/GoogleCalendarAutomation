from __future__ import print_function
import datetime
import requests
import json
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# -------------------------------
# Configuration
# -------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
# Replace with the actual calendar ID of your shared calendar
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID")  # e.g., "myemail@gmail.com"

# -------------------------------
# Google Calendar Service
# -------------------------------
def google_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS environment variable")

    try:
        creds_info = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid GOOGLE_CREDENTIALS JSON: {e}")

    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)
    
    # Debug: List accessible calendars
    calendars = service.calendarList().list().execute()
    print("Accessible calendars:", [c["summary"] for c in calendars.get("items", [])])
    
    return service

# -------------------------------
# Fetch Manchester City Matches
# -------------------------------
def fetch_matches():
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("Missing FOOTBALL_DATA_API_KEY environment variable")
    
    url = "https://api.football-data.org/v4/teams/65/matches?season=2025"
    headers = {"X-Auth-Token": api_key}
    
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    
    matches = resp.json().get("matches", [])
    print(f"Fetched {len(matches)} matches")
    return matches

# -------------------------------
# Fetch existing events
# -------------------------------
def fetch_calendar_events(service, calendar_id):
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

# -------------------------------
# Sync matches into Google Calendar
# -------------------------------
def sync_matches(service, matches, calendar_id):
    match_map = {str(m["id"]): m for m in matches}
    events = fetch_calendar_events(service, calendar_id)
    
    # Map match_id -> existing event
    existing_event_map = {}
    for e in events:
        summary = e.get("summary", "")
        for m_id, m in match_map.items():
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            if f"{home} vs {away}" in summary:
                existing_event_map[m_id] = e["id"]
                break

    # Add or update matches
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
            print(f"⚠️ HTTP Error syncing {title}: {e}")
        except Exception as e:
            print(f"⚠️ Unexpected Error syncing {title}: {e}")

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    if not CALENDAR_ID:
        raise ValueError("Missing GOOGLE_CALENDAR_ID environment variable")
    
    service = google_calendar_service()
    matches = fetch_matches()
    if matches:
        sync_matches(service, matches, CALENDAR_ID)
    else:
        print("No matches to sync")
