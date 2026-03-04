# Getting Started with Firebase & Firestore

This guide covers the minimal setup to enable Google login via Firebase Authentication and Firestore database access from a Python backend.

## Architecture Overview

```
User Browser
  → Firebase Authentication (Google login)
  → Browser receives Firebase ID Token
  → Backend verifies token
  → Backend reads/writes user data in Firestore
```

Key concepts:
- **Firebase UID** — stable unique identifier per user
- **Service Account** — identity used by the backend to access Firebase services
- **Firestore** — NoSQL database storing application data

---

## Step 1 — Create a Firebase Project

1. Go to [https://console.firebase.google.com/](https://console.firebase.google.com/)
2. Click **Add project**, choose a name (e.g. `missionary-lunch-calendar`)
3. Disable Google Analytics unless needed
4. Click **Create project**

---

## Step 2 — Enable Google Authentication

1. Navigate to **Build → Authentication → Get Started**
2. Open **Sign-in method** and select **Google**
3. Enable it, choose a support email, and **Save**

---

## Step 3 — Add Authorized Domains

Navigate to **Authentication → Settings → Authorized domains** and add every domain where the app will run, for example:

```
localhost
127.0.0.1
your-app.fly.dev
```

> Without this step Google login will fail.

---

## Step 4 — Register the Web Application

1. Go to **Project Settings (gear icon) → General → Your apps**
2. Click the **Web App** icon (`</>`)
3. Register a new web app — Firebase will provide a config object:

```js
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  ...
}
```

This configuration is public and safe to expose in your frontend.

---

## Step 5 — Enable Firestore Database

1. Navigate to **Build → Firestore Database → Create database**
2. Select **Native Mode**, choose a region, and click **Create**

---

## Step 6 — Create a Backend Service Account

1. Go to **Project Settings → Service Accounts**
2. Click **Generate new private key** — this downloads a `service-account.json` file

> ⚠️ **Never commit this file to git.** There is one service account per backend, not per user.

---

## Step 7 — Set Environment Variables

Since container filesystems are ephemeral, credentials must be injected via environment variables.

| Variable | Description |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full service account JSON, on a single line |
| `GOOGLE_CLOUD_PROJECT` | Firebase project ID |
| `FIRESTORE_COLLECTION` | Firestore collection name |

Example `.env` file:

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account","project_id":"missionary-lunch-calendar","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"..."}'
GOOGLE_CLOUD_PROJECT=missionary-lunch-calendar
FIRESTORE_COLLECTION=calendar_entries
```

**Formatting rules:**
- JSON must be on a **single line**
- `private_key` newlines must be escaped as `\n`
- JSON must be wrapped in **single quotes**

---

## Step 8 — Running with Docker

```bash
docker run --env-file .env your-image
```

Do not embed credentials inside the image.

---

## Step 9 — Running on Fly.io

```bash
fly secrets set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat service-account.json)"
```

Fly automatically injects the secret into the container environment.

---

## Step 10 — Python Initialization

```python
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

service_account = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
cred = credentials.Certificate(service_account)

firebase_admin.initialize_app(cred, {
    "projectId": os.environ["GOOGLE_CLOUD_PROJECT"]
})

db = firestore.client()
collection = db.collection(os.environ.get("FIRESTORE_COLLECTION", "calendar_entries"))
```

---

## Step 11 — User Identity Model

When a user authenticates with Google via Firebase, the backend receives a JWT ID token containing:

- `uid` — stable unique identifier (**use this as the primary key**)
- `email`, `name`, `picture`

Example Firestore structure:

```
calendar_entries
  └── {user_uid}
        └── entry documents
```

> Never use `email` as a primary identifier — it can change.

---

## Common Issues

### Google Sign-In failed

**Cause:** Domain not listed in Authorized Domains.  
**Fix:** Add the domain under **Authentication → Settings → Authorized domains**.

### Web App icon (`</>`) not visible

**Cause:** Firebase UI changed.  
**Fix:** Go to **Project Settings → General → Your apps** and scroll down to add the web app.

### Container cannot store credentials

**Cause:** Container filesystems are ephemeral.  
**Fix:** Use the `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable instead of a file path.
