# 🚀 Deployment Guide: Running CardioVoice Backend on a Fresh Machine

This guide details exactly how to take the CardioVoice Backend Docker image and run it on a completely new computer that has nothing but Docker installed.

---

## 🏗️ The Logic (ELI5)

1.  **The Box (Image)**: We don't move code files. We move the **Docker Image**, which is a sealed box containing the OS, Python, and the App.
2.  **The Fridge (Database)**: The App Box relies on a Database Box. We must start both and connect them.
3.  **The Blueprint (Compose)**: We use a special `docker-compose.deploy.yml` file to tell the new computer how to set up both boxes and wire them together.

---

## ✅ Prerequisites

On the new machine, you need **Docker Desktop** (or Docker Engine + Compose) installed.

## 🛠️ Step-by-Step Deployment

### 1. Prepare the Files
Create a new folder on the destination machine (e.g., `cardipvoice-deploy`) and copy these **two files** into it:

1.  `docker-compose.deploy.yml` (The Blueprint)
2.  `init_vector.sql` (The Database Switch - *Critical for pgvector*)

> **Why?** Since we aren't copying the source code, we need `init_vector.sql` to manually tell the fresh Postgres database to enable the "Vector" extension. Without this, the app crashes with `type "vector" does not exist`.

### 2. Configure Environment & Ports
Open a terminal in that folder. You must set 2 environment variables so Docker knows where to get the image and what API key to use.

**PowerShell (Windows):**
```powershell
$env:GIGACHAT_AUTH_KEY="your-real-key-here"
$env:GITHUB_REPOSITORY_OWNER="your-github-username"
```
**Bash (Linux/Mac):**
```bash
export GIGACHAT_AUTH_KEY="your-real-key-here"
export GITHUB_REPOSITORY_OWNER="your-github-username"
```

**Port Mapping Logic**:
In `docker-compose.deploy.yml`, check the `ports` section:
```yaml
ports:
  - "5010:5000"  # Host Port : Container Port
```
*   **5010** is the port you will type in your browser. You can change this to 8080, 3000, etc.
*   **5000** must stay 5000 (that's where the app lives inside the box).

### 3. The "Fresh Start" Launch (Critical)
Run this command to start everything:

```powershell
docker-compose -f docker-compose.deploy.yml up -d
```

> **Logic**:
> *   `docker-compose` reads the YAML file.
> *   It downloads the endpoint image from GHCR.
> *   It downloads the Postgres image.
> *   It creates a **Volume** (`postgres_data`) to store data.
> *   **First Run Magic**: Because the volume is new, Postgres runs `init_vector.sql`, enabling the vector extension.

### 4. Verification
Wait ~15 seconds, then check:

**A. Check the Logs**
```powershell
docker logs -f cardiovoice-api
```
*   **Success**: You see `✅ Database tables initialized` and `Listening at 0.0.0.0:5000`.
*   **Failure**: You see python tracebacks or `Could not connect`.

**B. Check the Browser**
Visit: `http://localhost:5010/health`
*   **Success**: `{"status": "ok", ...}`
*   **Success (Root)**: Visiting just `/` gives `{"code":"NOT_FOUND"}`. This is normal! The API has no home page.

---

## ⚠️ Common Pitfalls & Fixes

### Pitfall 1: "type 'vector' does not exist"
*   **Symptom**: App crashes on startup.
*   **Cause**: You started the database *before* you added `init_vector.sql` (or before it was mounted correctly). Postgres created the data folder, saw it wasn't empty on the second run, and **skipped** the init script.
*   **Fix**: You must delete the "tainted" volume to force a fresh init.
    ```powershell
    docker-compose -f docker-compose.deploy.yml down -v
    ```
    *(The `-v` flag deletes the volume. Data is lost, but the DB is reset)*.

### Pitfall 2: "Bind for 0.0.0.0:5000 failed: port is already allocated"
*   **Symptom**: Container fails to start.
*   **Cause**: You have another copy of the app running (maybe in another terminal) using port 5000 (or 5010).
*   **Fix**:
    1.  `docker ps` to find the old container ID.
    2.  `docker stop <ID>` to kill it.
    3.  Or verify `docker-compose.deploy.yml` uses a unique port (e.g., `5099:5000`).

### Pitfall 3: "Could not connect to PostgreSQL"
*   **Symptom**: Logs show "Attempt 30/30...".
*   **Cause**: You tried to run just the `api` container alone without the `db` service.
*   **Fix**: Always use `docker-compose ... up`, which guarantees both start together in the same network.
