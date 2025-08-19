import os
import json
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def google_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDENTIALS environment variable")
    creds_info = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)

def force_clean_calendar(service, calendar_id="primary"):
    deleted_count = 0
    while True:
        page_token = None
        events_to_delete = []

        while True:
            try:
                events_result = service.events().list(
                    calendarId=calendar_id,
                    pageToken=page_token,
                    maxResults=2500,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
            except HttpError as e:
                print(f"⚠️ Error fetching events: {e}")
                return

            events = events_result.get("items", [])
            for e in events:
                summary = e.get("summary", "")
                description = e.get("description", "")
                colorId = e.get("colorId", "")
                # Mark for deletion
                if "Manchester City" in summary or description.startswith("match_id:") or colorId == "7":
                    events_to_delete.append(e["id"])

            page_token = events_result.get("nextPageToken")
            if not page_token:
                break

        if not events_to_delete:
            break  # nothing left to delete

        for event_id in events_to_delete:
            try:
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                deleted_count += 1
            except HttpError as e:
                print(f"⚠️ Failed to delete event {event_id}: {e}")

        print(f"Deleted {len(events_to_delete)} events. Waiting for Google to update...")
        time.sleep(5)  # wait to ensure calendar cache is updated

    print(f"\n✅ Total events deleted: {deleted_count}")

if __name__ == "__main__":
    service = google_calendar_service()
    force_clean_calendar(service)
