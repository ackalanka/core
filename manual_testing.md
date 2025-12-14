# CardioVoice Backend - Manual Testing Guide

> **Created**: December 14, 2025  
> **Last Updated**: December 14, 2025 20:56  
> **Current Phase**: Phase 2 Complete

---

## 📋 Overview

This guide provides step-by-step instructions for manually testing newly implemented features outside the IDE. Each phase section includes detailed test cases with expected results.

---

## 🔧 Prerequisites

Before testing, ensure:

1. **Server is running**:
   ```powershell
   cd c:\Users\Akalanka\Desktop\Gigachat\Backend
   $env:FLASK_ENV='development'
   .\venv\Scripts\python.exe app.py
   ```

2. **Server output shows**:
   ```
   🚀 Starting CardioVoice Backend in development mode
   📊 Rate limit: 100 req/min
   📁 Max upload size: 10MB
   🔐 JWT expiration: 24 hours
   * Serving Flask app 'app'
   * Debug mode: on
   ```

3. **Tools available**:
   - PowerShell (Windows) or Terminal (Mac/Linux)
   - Optional: Postman, Insomnia, or curl

---

# ✅ Phase 1: Security & Configuration Testing

## 1.1 Health Check Endpoint

**Purpose**: Verify server is running and accessible.

### Test Case 1.1.1: Basic Health Check

**PowerShell**:
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/health"
```

**Expected Response**:
```json
{
  "status": "ok",
  "mode": "real",
  "version": "1.0.0"
}
```

**Pass Criteria**: 
- Status code: 200
- Returns `status: ok`
- Mode is `real` (if GIGACHAT_AUTH_KEY is set) or `mock`

---

## 1.2 Security Headers

**Purpose**: Verify security headers are present on all responses.

### Test Case 1.2.1: Check Security Headers

**PowerShell**:
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:5000/health"
$response.Headers["X-Content-Type-Options"]
$response.Headers["X-Frame-Options"]
$response.Headers["X-XSS-Protection"]
$response.Headers["Content-Security-Policy"]
$response.Headers["Referrer-Policy"]
```

**Expected Output**:
```
nosniff
DENY
1; mode=block
default-src 'self'; script-src 'self' 'unsafe-inline'; ...
strict-origin-when-cross-origin
```

**Pass Criteria**: All security headers are present with correct values.

---

## 1.3 User Registration

**Purpose**: Test new user account creation.

### Test Case 1.3.1: Successful Registration

**PowerShell**:
```powershell
$body = @{
    email = "testuser@example.com"
    password = "SecurePass123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Expected Response** (Status 201):
```json
{
  "status": "success",
  "message": "Registration successful",
  "data": {
    "user": {
      "id": "uuid-here",
      "email": "testuser@example.com",
      "created_at": "2025-12-14T..."
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**Pass Criteria**: 
- Status code: 201
- Returns user object with ID and email
- Returns valid JWT access_token

---

### Test Case 1.3.2: Duplicate Email Registration

**PowerShell** (run after 1.3.1):
```powershell
$body = @{
    email = "testuser@example.com"
    password = "AnotherPass456"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/register" `
        -Method POST -ContentType "application/json" -Body $body
} catch {
    $_.Exception.Response.StatusCode
    $streamReader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    $streamReader.ReadToEnd()
}
```

**Expected Response** (Status 400):
```json
{
  "status": "error",
  "message": "Email already registered",
  "code": "REGISTRATION_FAILED"
}
```

**Pass Criteria**: Returns 400 with appropriate error message.

---

### Test Case 1.3.3: Invalid Email Format

**PowerShell**:
```powershell
$body = @{
    email = "not-an-email"
    password = "SecurePass123"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/register" `
        -Method POST -ContentType "application/json" -Body $body
} catch {
    $_.Exception.Response.StatusCode
}
```

**Expected**: Status 400 with validation error.

---

### Test Case 1.3.4: Weak Password

**PowerShell**:
```powershell
$body = @{
    email = "newuser@example.com"
    password = "weak"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/register" `
        -Method POST -ContentType "application/json" -Body $body
} catch {
    Write-Host "Status: 400 (Expected)"
}
```

**Pass Criteria**: 
- Returns 400
- Error mentions password requirements (8+ chars, letter, digit)

---

## 1.4 User Login

**Purpose**: Test user authentication and token generation.

### Test Case 1.4.1: Successful Login

**PowerShell**:
```powershell
$body = @{
    email = "testuser@example.com"
    password = "SecurePass123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

# Store token for later tests
$token = $loginResponse.data.access_token
Write-Host "Token: $token"
```

**Expected Response** (Status 200):
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

**Pass Criteria**: Returns valid JWT token.

---

### Test Case 1.4.2: Invalid Password

**PowerShell**:
```powershell
$body = @{
    email = "testuser@example.com"
    password = "WrongPassword"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
        -Method POST -ContentType "application/json" -Body $body
} catch {
    Write-Host "Status: 401 (Expected - Invalid credentials)"
}
```

**Expected**: Status 401 with "Invalid email or password".

---

### Test Case 1.4.3: Non-existent User

**PowerShell**:
```powershell
$body = @{
    email = "nobody@example.com"
    password = "SomePassword123"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
        -Method POST -ContentType "application/json" -Body $body
} catch {
    Write-Host "Status: 401 (Expected - Same error to prevent enumeration)"
}
```

**Pass Criteria**: Returns same error as invalid password (prevents email enumeration).

---

## 1.5 Protected Endpoints

**Purpose**: Test JWT authentication on protected routes.

### Test Case 1.5.1: Access Without Token

**PowerShell**:
```powershell
try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/me" -Method GET
} catch {
    Write-Host "Status: 401 (Expected - No token provided)"
}
```

**Expected Response** (Status 401):
```json
{
  "status": "error",
  "message": "Authentication required. Please provide a valid token.",
  "code": "AUTH_REQUIRED"
}
```

---

### Test Case 1.5.2: Access With Valid Token

**PowerShell** (use token from login test):
```powershell
# First login to get token
$loginBody = @{ email = "testuser@example.com"; password = "SecurePass123" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
    -Method POST -ContentType "application/json" -Body $loginBody
$token = $loginResponse.data.access_token

# Access protected endpoint
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/me" `
    -Method GET -Headers $headers
```

**Expected Response** (Status 200):
```json
{
  "status": "success",
  "data": {
    "id": "uuid-here",
    "email": "testuser@example.com",
    "created_at": "2025-12-14T..."
  }
}
```

---

### Test Case 1.5.3: Access With Invalid Token

**PowerShell**:
```powershell
$headers = @{ Authorization = "Bearer invalid.token.here" }
try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/me" `
        -Method GET -Headers $headers
} catch {
    Write-Host "Status: 401 (Expected - Invalid token)"
}
```

**Expected**: Status 401 with "Invalid or expired token".

---

## 1.6 Rate Limiting

**Purpose**: Test that rate limiting prevents abuse.

### Test Case 1.6.1: Login Rate Limit (5 per minute)

**PowerShell**:
```powershell
$body = @{ email = "test@test.com"; password = "test" } | ConvertTo-Json

# Send 6 requests rapidly
for ($i = 1; $i -le 6; $i++) {
    try {
        $result = Invoke-WebRequest -Uri "http://localhost:5000/api/v1/auth/login" `
            -Method POST -ContentType "application/json" -Body $body
        Write-Host "Request $i : $($result.StatusCode)"
    } catch {
        Write-Host "Request $i : $($_.Exception.Response.StatusCode) (Rate limited)"
    }
}
```

**Expected**: First 5 requests return 401, 6th returns 429 (Too Many Requests).

---

### Test Case 1.6.2: Rate Limit Response

**Expected Response** (Status 429):
```json
{
  "status": "error",
  "message": "Rate limit exceeded. Please slow down.",
  "code": "RATE_LIMIT_EXCEEDED"
}
```

---

## 1.7 Protected Analysis Endpoint

**Purpose**: Verify /analyze requires authentication.

### Test Case 1.7.1: Analyze Without Token

**PowerShell**:
```powershell
try {
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/analyze" `
        -Method POST -ContentType "multipart/form-data"
} catch {
    Write-Host "Status: 401 (Expected - Auth required)"
}
```

**Pass Criteria**: Returns 401 AUTH_REQUIRED.

---

## 1.8 Input Validation

**Purpose**: Test file upload restrictions.

### Test Case 1.8.1: Oversized File Upload

**Note**: This test requires creating a large file first.

**PowerShell**:
```powershell
# Create a 15MB dummy file (exceeds 10MB limit)
$bytes = New-Object byte[] (15 * 1024 * 1024)
[System.IO.File]::WriteAllBytes("$PWD\large_test.bin", $bytes)

# Attempt upload (will fail at size check)
# The actual multipart upload is complex in PowerShell
# Use Postman/curl for easier testing
```

**Expected**: Server rejects with 413 or 400 "File too large".

---

## 1.9 OpenAPI Documentation

**Purpose**: Verify Swagger UI is accessible.

### Test Case 1.9.1: Access Swagger UI

**Browser**: Navigate to http://localhost:5000/docs

**Pass Criteria**: Swagger UI loads and shows API endpoints.

---

## 📊 Test Summary Template

Copy and fill out after testing:

```
Phase 1 Testing - [DATE]
========================

| Test Case | Result | Notes |
|-----------|--------|-------|
| 1.1.1 Health Check | ⬜ | |
| 1.2.1 Security Headers | ⬜ | |
| 1.3.1 Registration Success | ⬜ | |
| 1.3.2 Duplicate Email | ⬜ | |
| 1.3.3 Invalid Email | ⬜ | |
| 1.3.4 Weak Password | ⬜ | |
| 1.4.1 Login Success | ⬜ | |
| 1.4.2 Invalid Password | ⬜ | |
| 1.4.3 Non-existent User | ⬜ | |
| 1.5.1 Access Without Token | ⬜ | |
| 1.5.2 Access With Token | ⬜ | |
| 1.5.3 Invalid Token | ⬜ | |
| 1.6.1 Rate Limiting | ⬜ | |
| 1.7.1 Analyze Without Token | ⬜ | |
| 1.9.1 Swagger UI | ⬜ | |

Legend: ✅ Pass | ❌ Fail | ⬜ Not Tested
```

---

# 📝 Testing with Postman/Insomnia

For easier testing, you can import these as a collection:

## Environment Variables
```
BASE_URL: http://localhost:5000
TOKEN: (set after login)
```

## Requests

### Register
- **Method**: POST
- **URL**: {{BASE_URL}}/api/v1/auth/register
- **Body** (JSON):
```json
{
  "email": "test@example.com",
  "password": "SecurePass123"
}
```

### Login
- **Method**: POST
- **URL**: {{BASE_URL}}/api/v1/auth/login
- **Body** (JSON):
```json
{
  "email": "test@example.com",
  "password": "SecurePass123"
}
```
- **Post-request Script**: `pm.environment.set("TOKEN", pm.response.json().data.access_token)`

### Get Me
- **Method**: GET
- **URL**: {{BASE_URL}}/api/v1/auth/me
- **Headers**: `Authorization: Bearer {{TOKEN}}`

### Analyze
- **Method**: POST
- **URL**: {{BASE_URL}}/api/v1/analyze
- **Headers**: `Authorization: Bearer {{TOKEN}}`
- **Body** (form-data):
  - age: 45
  - gender: male
  - smoking_status: non-smoker
  - activity_level: moderate
  - audio: [file upload]

# ✅ Phase 2: Database Migration Testing

## Prerequisites

Before testing Phase 2, ensure Docker Desktop is installed and running.

---

## 2.1 Docker PostgreSQL Setup

**Purpose**: Verify PostgreSQL container starts correctly.

### Test Case 2.1.1: Start Database Container

**PowerShell**:
```powershell
cd c:\Users\Akalanka\Desktop\Gigachat\Backend
docker-compose up -d
```

**Expected Output**:
```
[+] Running 2/2
 ✔ Volume "cardiovoice_postgres_data" Created
 ✔ Container cardiovoice-db Started
```

### Test Case 2.1.2: Check Container Status

**PowerShell**:
```powershell
docker ps --filter name=cardiovoice-db
```

**Expected**: Container is running with status `Up`.

### Test Case 2.1.3: Check pgvector Extension

**PowerShell**:
```powershell
docker exec cardiovoice-db psql -U cardiovoice -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Expected**: Returns row showing `vector` extension is installed.

---

## 2.2 Knowledge Base Migration

**Purpose**: Verify JSON data migrates to database correctly.

### Test Case 2.2.1: Run Migration Script

**PowerShell**:
```powershell
.\venv\Scripts\python.exe scripts/migrate_knowledge_base.py
```

**Expected Output**:
```
==================================================
CardioVoice Knowledge Base Migration
==================================================
📦 Initializing database tables...
📖 Loading knowledge_base.json...
   Found 4 conditions
   ✅ Created condition: АГ
   ✅ Created condition: СД2
   ✅ Created condition: ИБС
   ✅ Created condition: Пост-ОИМ (1–3 мес)

✅ Migration complete!
   Conditions created: 4
   Supplements created: X

🔍 Verifying migration...
   Total conditions: 4
   Total supplements: X
```

### Test Case 2.2.2: Verify Data in Database

**PowerShell**:
```powershell
docker exec cardiovoice-db psql -U cardiovoice -c "SELECT code, name FROM conditions;"
```

**Expected**: Lists all 4 conditions.

**PowerShell**:
```powershell
docker exec cardiovoice-db psql -U cardiovoice -c "SELECT COUNT(*) FROM supplements;"
```

**Expected**: Returns count > 0.

---

## 2.3 User Persistence (Critical Test!)

**Purpose**: Verify users survive server restarts.

### Test Case 2.3.1: Register → Restart → Login

**Step 1 - Register a new user**:
```powershell
$body = @{
    email = "persistent@test.com"
    password = "SecurePass123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/register" `
    -Method POST -ContentType "application/json" -Body $body
```

**Step 2 - Restart the server**:
```powershell
# Stop current server (Ctrl+C in terminal running app.py)
# Then restart:
.\venv\Scripts\python.exe app.py
```

**Step 3 - Login with same user**:
```powershell
$body = @{
    email = "persistent@test.com"
    password = "SecurePass123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
    -Method POST -ContentType "application/json" -Body $body
```

**Pass Criteria**: 
- Login succeeds after restart
- Returns valid JWT token
- User was NOT lost

---

## 2.4 Supplement Query from Database

**Purpose**: Verify knowledge base queries use database.

### Test Case 2.4.1: Check Server Logs

When server starts, look for:
```
Knowledge Base loaded from database: X supplements
```

NOT:
```
Knowledge Base loaded from JSON: 4 categories.
```

### Test Case 2.4.2: Analyze Endpoint Uses Database

**PowerShell**:
```powershell
# Login first
$loginBody = @{ email = "persistent@test.com"; password = "SecurePass123" } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/v1/auth/login" `
    -Method POST -ContentType "application/json" -Body $loginBody
$token = $loginResponse.data.access_token

# Check server logs after making request
# Should show: "KB Database Search" not "KB JSON Search"
```

---

## 2.5 Database Fallback

**Purpose**: Verify JSON fallback when database is unavailable.

### Test Case 2.5.1: Stop Database → Server Uses JSON

**PowerShell**:
```powershell
# Stop database
docker-compose down

# Restart server
.\venv\Scripts\python.exe app.py
```

**Expected Log Output**:
```
Database not available: ... Using JSON fallback.
Knowledge Base loaded from JSON: 4 categories.
```

**Pass Criteria**: Server starts successfully using JSON file.

---

## 📊 Phase 2 Test Summary Template

```
Phase 2 Testing - [DATE]
========================

| Test Case | Result | Notes |
|-----------|--------|-------|
| 2.1.1 Start Container | ⬜ | |
| 2.1.2 Container Status | ⬜ | |
| 2.1.3 pgvector Extension | ⬜ | |
| 2.2.1 Run Migration | ⬜ | |
| 2.2.2 Verify Data | ⬜ | |
| 2.3.1 User Persistence | ⬜ | CRITICAL |
| 2.4.1 Server Logs | ⬜ | |
| 2.4.2 Database Query | ⬜ | |
| 2.5.1 JSON Fallback | ⬜ | |

Legend: ✅ Pass | ❌ Fail | ⬜ Not Tested
```

---

# 🔜 Future Phases

Sections will be added as phases are implemented:

- [x] Phase 1: Security & Configuration Testing
- [x] Phase 2: Database Migration Testing
- [ ] Phase 2.5: RAG Implementation Testing
- [ ] Phase 3: Testing Infrastructure
- [ ] Phase 4: ML Model Integration Testing
- [ ] Phase 5: Container Testing
- [ ] Phase 6: CI/CD Pipeline Testing
- [ ] Phase 7: Cloud Deployment Testing
- [ ] Phase 8: Observability Testing

---

*Last Updated: 2025-12-14 20:56*

*This document is updated after each phase implementation.*
