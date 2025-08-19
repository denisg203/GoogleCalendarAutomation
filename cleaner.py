from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def google_calendar_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("calendar", "v3", credentials=creds)

def delete_synced_events(service, calendar_id="primary"):
    page_token = None
    count = 0

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
            # Delete events that contain Manchester City (home or away)
            if "Manchester City" in summary:
                service.events().delete(calendarId=calendar_id, eventId=e["id"]).execute()
                print(f"🗑️ Deleted: {summary}")
                count += 1

        page_token = events_result.get("nextPageToken")
        if not page_token:
            break

    print(f"\n✅ Deleted {count} synced events.")

if __name__ == "__main__":
    service = google_calendar_service()
    delete_synced_events(service)
