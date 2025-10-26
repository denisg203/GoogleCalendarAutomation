# Manchester City - Google Calendar Sync Automation

A fully automated CI/CD pipeline that syncs sports fixtures to Google Calendar using Python, Google APIs, and GitHub Actions.

### Project Summary

This project is a robust, event-scheduling solution that autonomously fetches Manchester City's match fixtures from the **Football-Data.org REST API** and synchronizes them with a designated Google Calendar.

The primary goal is to maintain an always-up-to-date calendar by intelligently adding new matches, updating rescheduled events, and removing canceled fixtures. The entire process is fully automated, running on a weekly schedule via a **GitHub Actions CI/CD workflow**.

---

### Key Features & Technical Skills

* **CI/CD Automation:** Utilizes **GitHub Actions** for scheduled, autonomous execution. The workflow runs every Friday at 10:00 UTC to ensure the calendar is always accurate.
* **Dual API Integration:**
    * Consumes the **Football-Data.org REST API** (Team ID 65) for external data retrieval.
    * Integrates with the **Google Calendar API** for complex calendar manipulation (Create, Read, Update, Delete - CRUD operations).
* **Intelligent Sync Logic:** The script performs a "smart sync" by comparing existing calendar events against the newly fetched data. It idempotently adds new fixtures, updates events with new times (e.g., postponed matches), and removes canceled matches.
* **Secure Credential Management:** All sensitive data (API keys, Google service account credentials, calendar IDs) is securely managed using **GitHub Encrypted Secrets**. No secrets are hardcoded in the repository, adhering to security best practices.
* **Python Scripting:** Built with clean, modular Python, handling API requests, JSON parsing, error handling, and datetime manipulation.

---

### Workflow Architecture

1.  **Trigger:** The GitHub Actions workflow is triggered on a weekly schedule (`cron`) or by manual dispatch (`workflow_dispatch`).
2.  **Environment Setup:** The job checks out the repository, sets up a Python environment, and installs dependencies from `requirements.txt`.
3.  **Authentication:** Secure credentials for all services (Google API, Football API, Email) are loaded from GitHub Secrets into environment variables.
4.  **Data Fetching:** The `sync_mancity.py` script calls the Football-Data.org API to get the latest fixture list.
5.  **Calendar Sync:**
    * The script authenticates with the Google Calendar API using a Service Account.
    * It fetches all existing fixture events from the target calendar.
    * It intelligently compares the fetched fixtures with the calendar events.
    * It performs the necessary **CRUD operations**: `INSERT` new matches, `UPDATE` rescheduled/postponed matches, and `DELETE` canceled matches.
6.  **Notification:** The workflow automatically sends an email notification indicating the success or failure of the sync operation.

---

### Technology Stack

* **Language:** Python
* **Automation/CI/CD:** GitHub Actions
* **APIs:** Google Calendar API, Football-Data.org API
* **Core Libraries:** `google-api-python-client`, `google-auth-oauthlib`, `requests`
* **Security:** GitHub Encrypted Secrets

### Extensibility & Notes

* **Modular Design:** The script is easily adaptable for any other sports team by simply changing the team ID in `sync_mancity.py`.
* **Safe Operations:** The script is designed to only manage events it creates and will not modify or delete any unrelated personal events on the calendar.

### License

This project is released under the MIT License — feel free to use, modify, and share it.
