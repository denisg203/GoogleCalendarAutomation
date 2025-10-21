🏟️ Manchester City Fixture Sync — Google Calendar Automation

This project automatically syncs Manchester City’s fixtures from the Football-Data.org API
 directly into Google Calendar using the Google Calendar API.

It keeps your calendar up to date by adding, updating, or removing events whenever fixtures are announced, rescheduled, or canceled.

The sync runs automatically every Friday at 10:00 UTC via GitHub Actions.

⚙️ Features

🔄 Weekly automatic updates — fetches the latest Manchester City fixtures

🗓️ Google Calendar integration — creates or updates events seamlessly

🧠 Smart sync — detects postponed or canceled matches and updates them accordingly

🔐 Secure — credentials and API keys are stored safely as GitHub Secrets (never exposed in the repo)

☁️ Fully automated — no manual intervention once configured

🚀 How It Works

Fetch data from the Football-Data.org API for Manchester City (Team ID 65).

Process matches and build corresponding Google Calendar events.

Compare existing events and apply necessary additions, updates, or deletions.

Run automatically every Friday using GitHub Actions.

🧩 Project Structure
.
├── sync_mancity.py        # Main Python script for syncing matches
├── requirements.txt       # Dependencies
├── .github/
│   └── workflows/
│       └── sync_mancity.yml  # GitHub Actions workflow
└── README.md

🧠 Notes

The script only manages events it created; it won’t modify unrelated calendar entries.

You can easily adapt it for other teams by changing the team ID in sync_mancity.py.

All API credentials are handled securely — no sensitive data is stored in the repo.

📄 License

This project is released under the MIT License — feel free to use, modify, and share it.
