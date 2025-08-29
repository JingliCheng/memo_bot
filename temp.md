Sweet — let’s ship the **backend** to Cloud Run. You’ll still keep iterating on the UI locally or anywhere you like.

I’ll give you only what you need:

* the two small files to add,
* the exact `gcloud` commands,
* the 3 post-deploy tweaks (CORS, Firebase Auth domains, frontend baseUrl),
* and a sanity test.

---

# 1) Files to add in `backend/`

## `backend/requirements.txt`

(use your exact versions if you have them)

```
fastapi
uvicorn
python-dotenv
openai
google-cloud-firestore
google-auth
firebase-admin
```

## `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

# System deps (optional but handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY backend/ ./

# Cloud Run sets $PORT; default to 8080 for local docker run
ENV PORT=8080

# Start FastAPI via Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

*(Your `main.py` already reads envs and uses ADC; no code changes needed.)*

---

# 2) One-time project setup

```bash
# pick your project and region
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"   # or your favorite region

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com secretmanager.googleapis.com firestore.googleapis.com iamcredentials.googleapis.com
```

Create the OpenAI key in **Secret Manager** (or add a new version if it exists):

```bash
# If creating new:
echo -n "$OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-

# If the secret already exists, add a version:
# echo -n "$OPENAI_API_KEY" | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

---

# 3) Build and deploy to Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/ai-companion-backend

# Deploy
gcloud run deploy ai-companion-backend \
  --image gcr.io/$PROJECT_ID/ai-companion-backend \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars OPENAI_MODEL=gpt-4o-mini \
  --set-env-vars WEB_ORIGIN=http://localhost:5173 \
  --update-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest
```

> This prints a **Service URL** like `https://ai-companion-backend-xxxx-uc.a.run.app`. Keep it.

### Grant the service account access to the secret (if needed)

Cloud Run uses a service account (often `${PROJECT_NUMBER}-compute@developer.gserviceaccount.com`). Give it **Secret Accessor**:

```bash
SA="$(gcloud run services describe ai-companion-backend --region $REGION --format='value(spec.template.spec.serviceAccountName)')"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor"
```

*(Re-deploy if you just added the role.)*

Firestore access usually works by default; if not, grant the SA:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/datastore.user"
```

---

# 4) Frontend tweaks (so it talks to Cloud Run)

* In your React app, set:

  ```js
  const baseUrl = "https://<your-cloud-run-url>";
  ```
* In **Firebase Console → Authentication → Settings → Authorized domains**, add your **frontend** domain (e.g., `localhost`, `your-frontend-host.com`).
  *(This is for sign-in; Cloud Run URL does not need to be there.)*
* On the **backend**, set CORS to your real frontend when you deploy the UI:

  * Re-deploy with:
    `--set-env-vars WEB_ORIGIN=https://your-frontend-host.com`

---

# 5) Sanity test

* Health (no auth needed):

  ```bash
  curl -s https://<cloud-run-url>/health
  # -> {"ok": true}
  ```

* Whoami (requires Firebase ID token):

  * In your browser console on the running UI:

    ```js
    // after the page signs in anonymously
    const t = await (await import('./src/firebase.js')).then(m => m.auth.currentUser.getIdToken());
    t
    ```
  * Then:

    ```bash
    curl -s https://<cloud-run-url>/whoami \
      -H "Authorization: Bearer <PASTE_TOKEN_HERE>"
    # -> {"uid":"..."}
    ```

* In the UI, update `baseUrl` and refresh. Memory/Recent should work; Chat should stream.

---

# 6) After it’s live

* **Keep iterating the UI** freely — it just talks to the Cloud Run URL.
* For future server updates: re-run the same **build + deploy** commands. Cloud Run will create a new revision with zero downtime.
* When you host the frontend (Vercel/Netlify/Firebase Hosting), re-deploy the backend with:

  ```
  --set-env-vars WEB_ORIGIN=https://your-frontend-domain
  ```

  and add that domain to Firebase Auth **Authorized domains**.

---

If you want, I can also give you a tiny **Add Memory** form for the UI so you don’t need curl/Postman when demoing. Or we can set up a **production** CORS + env profile now.
