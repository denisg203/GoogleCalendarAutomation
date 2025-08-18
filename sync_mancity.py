from __future__ import print_function
import datetime
import requests
import json
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# Google Calendar API setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TEAM_ID = 65  # Manchester City
SEASON = 2025

# List of competitions codes (add more if needed)
COMPETITIONS = ["PL", "CL"]

def google_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS environment variable")
    creds_info = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

def fetch_all_matches():
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("Missing FOOTBALL_DATA_API_KEY environment variable")

    headers = {"X-Auth-Token": api_key}
    all_matches = []

    for comp in COMPETITIONS:
        url = f"https://api.football-data.org/v4/competitions/{comp}/matches?season={SEASON}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        matches = response.json()["matches"]
        # Filter only Man City matches
        mc_matches = [m for m in matches if m["homeTeam"]["id"] == TEAM_ID or m["awayTeam"]["id"] == TEAM_ID]
        all_matches.extend(mc_matches)

    return all_matches

def fetch_calendar_events(service, calendar_id="primary"):
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

def sync_matches(service, matches, calendar_id="primary"):
    match_map = {str(m["id"]): m for m in matches}
    events = fetch_calendar_events(service, calendar_id)
    existing_event_map = {}

    for e in events:
        summary = e.get("summary", "")
        for m_id, m in match_map.items():
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            if f"{home} vs {away}" in summary:
                existing_event_map[m_id] = e["id"]
                break

    for match_id, m in match_map.items():
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        competition = m["competition"]["name"]
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
        title = f"[{competition}] {home} vs {away}"
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
            print(f"⚠️ Error syncing {title}: {e}")

    # Remove stale events
    stale_ids = set(existing_event_map.keys()) - set(match_map.keys())
    for stale_id in stale_ids:
        try:
            service.events().delete(calendarId=calendar_id, eventId=existing_event_map[stale_id]).execute()
            print(f"🗑️ Deleted stale event with ID {stale_id}")
        except Exception as e:
            print(f"⚠️ Error deleting stale event {stale_id}: {e}")

if __name__ == "__main__":
    service = google_calendar_service()
    matches = fetch_all_matches()
    sync_matches(service, matches)
