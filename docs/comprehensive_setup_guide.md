# 📘 Comprehensive Setup Guide: Consumer vs. Developer

## 👋 Introduction (Read This First)

There are two ways to run this project. Choose the path that matches you:

### 🅰️ Path A: The Consumer (Tester/User)
*   **Goal**: You just want to **RUN** the app to test it.
*   **Analogy**: Ordering a frozen pizza. You put it in the oven (Docker) and eat.
*   **Files You Need**: Just the "Release Bundle" (3 small files).
*   **Difficulty**: ⭐ (Easy)

### 🅱️ Path B: The Developer (Engineer)
*   **Goal**: You want to **CHANGE** the code or fix bugs.
*   **Analogy**: Cooking from scratch. You buy flour, tomatoes, cheese (Source Code) and make the pizza.
*   **Files You Need**: The entire GitHub Repository (Git Clone).
*   **Difficulty**: ⭐⭐⭐ (Medium)

---

# 🅰️ Path A: The Consumer (Deployment)

**Prerequisites**: You only need **Docker Desktop** installed.

### Step 1: Get the Release Bundle
You do NOT need to download the code. Ask the developer for the **Release Zip**, which contains only these 3 files:
1.  `run.bat` (The "Start Button")
2.  `docker-compose.deploy.yml` (The Instructions)
3.  `init_vector.sql` (The Database Configuration)

### Step 2: Unzip & Run
1.  Unzip the folder to your Desktop.
2.  Double-click `run.bat`.
3.  **First Time Only**: It will ask for credentials:
    *   **GigaChat Key**: The API key for the AI service.
    *   **GitHub Username**: The username of the person who built the image (e.g., `akalanka`).

### Step 3: Use the App
*   Wait about 30 seconds.
*   Open your browser to: `http://localhost:5010/docs`
*   **Success**: You see the "Swagger UI" page.

### 🛑 Troubleshooting Path A
*   **"Type 'vector' does not exist"**: You ran the app *before* having `init_vector.sql`.
    *   **Fix**: Run `docker-compose -f docker-compose.deploy.yml down -v` to delete the broken database and try again.
*   **"Port already allocated"**: Something else is running on port 5010 or 5000.
    *   **Fix**: Restart your computer or use `docker ps` to kill old containers.

---

# 🅱️ Path B: The Developer (Source Code)

**Prerequisites**: Git, Docker Desktop, VS Code (optional but recommended).

### Step 1: Get the Source Code (Cloning)
You are not downloading a zip; you are linking to the project history.
Open your terminal (PowerShell/Bash) and run:

```bash
git clone https://github.com/your-username/cardiovoice-backend.git
cd cardiovoice-backend
```

### Step 2: Create Environment File
You need a `.env` file for secrets. Developers typically copy the example:

**Windows**:
```powershell
copy .env.example .env
```
**Mac/Linux**:
```bash
cp .env.example .env
```
*Now open `.env` in Notepad/VS Code and put in your real `GIGACHAT_AUTH_KEY`.*

### Step 3: Build and Run
Since you have the *raw ingredients* (code), you must "Bake" (Build) them into a container on your machine.

```bash
docker-compose up --build
```

> **Why `--build`?**
> This tells Docker: "Read the `Dockerfile`, download Python, install all libraries in `requirements.txt`, and create a new image specifically for me."
> This takes 5-10 minutes the first time.

### Step 4: Connecting the Frontend (Optional)
As a developer, you might verify the backend at: `http://localhost:5000/docs`.
(Note: Developers usually default to port **5000**, while deployments might change it).

### 🛑 Troubleshooting Path B
*   **"No space left on device"**: Building images takes space.
    *   **Fix**: run `docker system prune` to clear checking.
*   **Code changes don't show up**:
    *   If relying on standard Docker, you must restart `docker-compose up` to see changes.
    *   (Advanced developers mount volumes to see live changes).

---

# 🧠 Key Concepts (ELI5)

| Concept | The Analogy | Explanation |
| :--- | :--- | :--- |
| **Image** | The Frozen Pizza | A sealed, ready-to-run package. Contains the app + basic tools. |
| **Container** | The Oven | When you put an Image in Docker, it becomes a "Container" (a running process). |
| **Volume** | The Fridge | Containers are temporary; if you delete them, data is lost. Volumes are permanent storage folders (like for the Database). |
| **Port Mapping** | House Number | `5010:5000`. "If someone knocks on House 5010 (My Laptop), send them to Room 5000 (The Container)". |
| **Compose File** | The Recipe Card | A simple text file that lists: "I need 1 Database and 1 Web Server, connected together." |

---

# 🎯 Summary Verification

**Are you a Tester?**
1. Get the Zip.
2. Run `run.bat`.
3. Done.

**Are you a Coder?**
1. `git clone ...`
2. Configure `.env`.
3. `docker-compose up --build`.
