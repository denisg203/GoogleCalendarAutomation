import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def google_calendar_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("calendar", "v3", credentials=creds)

def deep_clean_calendar(service, calendar_id="primary"):
    page_token = None
    total_deleted = 0

    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            pageToken=page_token,
            maxResults=2500,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        for e in events:
            summary = e.get("summary", "")
            description = e.get("description", "")
            extended_props = e.get("extendedProperties", {})

            # Delete any event related to Manchester City (home or away)
            if "Manchester City" in summary or "match_id:" in description or extended_props:
                try:
                    service.events().delete(calendarId=calendar_id, eventId=e["id"]).execute()
                    total_deleted += 1
                    print(f"🗑️ Deleted: {summary}")
                except Exception as ex:
                    print(f"⚠️ Failed to delete {summary}: {ex}")

        page_token = events_result.get("nextPageToken")
        if not page_token:
            break

    print(f"\n✅ Deep-clean completed. Total events deleted: {total_deleted}")

if __name__ == "__main__":
    service = google_calendar_service()
    deep_clean_calendar(service)
