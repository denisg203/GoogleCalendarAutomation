import os
import json
import datetime
import time
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# -------------------------
# Google Calendar setup
# -------------------------
def google_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS environment variable")
    creds_info = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

# -------------------------
# Fetch Manchester City matches
# -------------------------
def fetch_matches():
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("Missing FOOTBALL_DATA_API_KEY environment variable")
    url = "https://api.football-data.org/v4/teams/65/matches?season=2025"
    headers = {"X-Auth-Token": api_key}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["matches"]

# -------------------------
# Fetch existing calendar events
# -------------------------
def fetch_calendar_events(service, calendar_id="primary"):
    events = []
    page_token = None
    while True:
        try:
            result = service.events().list(
                calendarId=calendar_id,
                maxResults=2500,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token
            ).execute()
        except HttpError as e:
            print(f"⚠️ Error fetching events: {e}")
            break
        events.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return events

# -------------------------
# Sync matches intelligently with retry
# -------------------------
def sync_matches(service, matches, calendar_id="primary", retries=3, delay=3):
    match_map = {str(m["id"]): m for m in matches}
    events = fetch_calendar_events(service, calendar_id)

    existing_event_map = {}
    for e in events:
        desc = e.get("description", "")
        if desc.startswith("match_id:"):
            m_id = desc.split("match_id:")[-1].strip()
            existing_event_map[m_id] = e["id"]
        elif e.get("colorId") == "7" and "Manchester City" in e.get("summary", ""):
            try:
                service.events().delete(calendarId=calendar_id, eventId=e["id"]).execute()
                print(f"🗑️ Deleted leftover event: {e.get('summary')}")
            except HttpError:
                pass

    for match_id, m in match_map.items():
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        status = m["status"]

        if status == "CANCELLED" and match_id in existing_event_map:
            try:
                service.events().delete(calendarId=calendar_id, eventId=existing_event_map[match_id]).execute()
                print(f"🗑️ Deleted cancelled match: {home} vs {away}")
            except HttpError as e:
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

        for attempt in range(retries):
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
                break  # success, exit retry loop
            except HttpError as e:
                print(f"⚠️ Attempt {attempt+1} failed for {title}: {e}")
                time.sleep(delay)
        else:
            print(f"❌ Failed to sync {title} after {retries} attempts.")

if __name__ == "__main__":
    service = google_calendar_service()
    print("⚽ Fetching matches...")
    matches = fetch_matches()
    print("📅 Syncing matches with retries...")
    sync_matches(service, matches)
    print("\n🎉 Done! Calendar is up to date.")
