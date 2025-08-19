from __future__ import print_function
import datetime
import requests
import json
import os
from datetime import datetime
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

def current_season():
    year=datetime.now().year
    month=datetime.now().month
    if month>=8:
        return year
    else:
        return year-1

# Fetch Manchester City matches from API-Football (RapidAPI)
def fetch_matches():
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        raise ValueError("Missing RAPIDAPI_KEY environment variable")

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    season = current_season()
    querystring = {"team": "50", "season": str(season)}  # Man City

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 403:
            print("⚠️ 403 Forbidden! Response body from API:")
            print(response.text)  # This will show why it’s forbidden
            raise Exception("API request forbidden. Check key, host, or plan limits.")
        response.raise_for_status()
        data = response.json()
        return data["response"]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Request failed: {e}")
        raise

def fetch_calendar_events(service, calendar_id="primary"):
    events_result = service.events().list(
        calendarId=calendar_id,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])


# Sync API-Football matches into Google Calendar
def sync_matches(service, matches, calendar_id="primary"):
    # Build a dict of match_id -> match
    match_map = {str(m["fixture"]["id"]): m for m in matches}

    # Get existing events
    events = fetch_calendar_events(service, calendar_id)
    existing_event_map = {}
    for e in events:
        summary = e.get("summary", "")
        for m_id, m in match_map.items():
            home = m["teams"]["home"]["name"]
            away = m["teams"]["away"]["name"]
            if f"{home} vs {away}" in summary:
                existing_event_map[m_id] = e["id"]
                break

    # Step 1: Add or update matches
    for match_id, m in match_map.items():
        fixture = m["fixture"]
        home = m["teams"]["home"]["name"]
        away = m["teams"]["away"]["name"]
        league = m["league"]["name"]
        status = fixture["status"]["short"]

        if status == "CANC":
            # Cancelled match
            if match_id in existing_event_map:
                try:
                    service.events().delete(calendarId=calendar_id, eventId=existing_event_map[match_id]).execute()
                    print(f"🗑️ Deleted (cancelled): {home} vs {away}")
                except Exception as e:
                    print(f"⚠️ Error deleting {home} vs {away}: {e}")
            continue

        # Build event
        start_dt = datetime.datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        end_dt = start_dt + datetime.timedelta(hours=2)
        title = f"{league}: {home} vs {away}"
        if status == "PST":
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

    # Step 2: Remove stale events
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
