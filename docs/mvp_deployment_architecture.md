# 🌐 MVP Deployment Architecture: The "Real World" Guide

## 1. The Big Picture (ELI5)

In a professional MVP (Minimum Viable Product), we stop running things on "My Laptop" and start running them on "The Cloud".

We use a **Decoupled Architecture**:
*   **The Frontend (The Face)**: Lives in a "Content Delivery Network" (CDN). It's just static files (HTML/JS) copied to hundreds of servers worldwide. It's fast and cheap.
*   **The Backend (The Brain)**: Lives on a "PaaS" (Platform as a Service). It's a powerful server running your Docker container.
*   **The Database (The Memory)**: Lives on a managed cloud database server.

### The Analogy: The Restaurant Chain
*   **Frontend (Menu)**: Printed copies are everywhere (CDN). Anyone can pick one up instantly.
*   **Backend (Kitchen)**: There is one central kitchen (Server) processing orders.
*   **User**: Looks at the Menu (Frontend), sends an order to the Kitchen (Backend).

---

## 2. The Workflow: "Git-Triggered Deployment"

We don't drag-and-drop files. We use **Automation**.

### The Developer Experience (You)
1.  You write code on your laptop.
2.  You verify it works.
3.  You type: `git push origin main`.
4.  **You are done.** Move on to the next task.

### The Cloud Experience (The Magic)
As soon as you push, the Cloud services wake up:
1.  **Backend Cloud (e.g. Railway)**:
    *   Detects the change.
    *   Downloads your code.
    *   Builds the Docker Image.
    *   Updates the running server without downtime.
2.  **Frontend Cloud (e.g. Vercel)**:
    *   Detects the change.
    *   Builds the React app.
    *   Updates the files on servers worldwide.

### The User Experience (The Customer)
1.  They just visit `https://www.cardiovoice.com`.
2.  They instantly see the new version.
3.  They install nothing.

---

## 3. Detailed Setup Steps (How to achieve this)

### Part A: The Backend (Railway/Render)
*Goal: Get `https://api.cardiovoice.com` running.*

1.  **Account**: Sign up for **Railway.app** (Simplest for Docker).
2.  **Database**: Click "New" -> "PostgreSQL".
    *   *Intricacy*: This gives you a `DATABASE_URL` (e.g. `postgresql://user:pass@railway.app:5432/db`).
3.  **Service**: Click "New" -> "GitHub Repo" -> Select `cardiovoice-backend`.
4.  **Variables**: In settings, paste your keys:
    *   `DATABASE_URL`: (Paste the one from step 2)
    *   `GIGACHAT_AUTH_KEY`: (Your real key)
    *   `ALLOWED_ORIGINS`: `https://www.cardiovoice.com` (Crucial for security!)
5.  **Deploy**: Railway automatically finds your `Dockerfile` and runs it.

### Part B: The Frontend (Vercel)
*Goal: Get `https://www.cardiovoice.com` running.*

1.  **Account**: Sign up for **Vercel.com**.
2.  **Import**: Click "Add New" -> "Project" -> Select your `cardiovoice-frontend` repo.
3.  **Variables**:
    *   `VITE_API_URL`: `https://api.cardiovoice.com` (Tells the frontend where the kitchen is).
4.  **Deploy**: Click "Deploy". Vercel builds the site in seconds.

---

## 4. Intricacies & "Gotchas"

### 1. CORS (Cross-Origin Resource Sharing)
*   **The Problem**: Browsers block House A (Frontend) from talking to House B (Backend) for security.
*   **The Fix**: You must tell the Backend explicitly: "It is okay to talk to `https://www.cardiovoice.com`".
*   **Where**: In Backend ENV variables (`ALLOWED_ORIGINS`).

### 2. Database Migrations
*   **The Problem**: Your code changed the database structure, but the Cloud DB is old.
*   **The Fix**: Your startup script (`entrypoint.sh`) usually handles this automatically (using tools like `alembic` or your custom `init_db`).

### 3. HTTPS / SSL
*   **Good News**: Cloud providers (Railway/Vercel) handle this **automatically**. You get free SSL certificates. You don't need to configure Nginx or Certbot manually anymore.

---

## 5. Options Comparison

| Provider | Best For | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Railway** | **You (MVP)** | Easiest Docker support, includes Database. | Costs ~$5/mo after trial. |
| **Render** | Alternative | Good free tier for web services. | Builds can be slow. |
| **AWS** | Enterprise | Unlimited power. | Extremely complex. Needs a PhD to setup. |
| **Vercel** | Frontend | The industry standard for React. Free. | Frontend only. |

**Verdict**: Use **Railway** (Backend + DB) + **Vercel** (Frontend).
