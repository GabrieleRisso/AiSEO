# AiSEO Railway Deployment Guide

Deploy both backend and frontend to Railway in under 5 minutes.

## Prerequisites

1. A [Railway account](https://railway.app) (free tier available)
2. This repository pushed to GitHub

## Quick Deploy (Recommended)

### Option 1: One-Click Deploy via Railway Dashboard

1. **Login to Railway**: https://railway.app/dashboard

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account and select this repository

3. **Deploy Backend First**:
   - Railway will auto-detect the project
   - Click "Add a Service" → "GitHub Repo"
   - Set **Root Directory**: `backend`
   - Railway will use the `backend/railway.json` config automatically

4. **Add PostgreSQL Database**:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL` environment variable

5. **Configure Backend Environment Variables**:
   - Click on the backend service → "Variables"
   - Add these variables:
   ```
   CORS_ORIGINS=https://YOUR_FRONTEND_URL.up.railway.app,http://localhost:5173
   LOG_LEVEL=INFO
   DEBUG=false
   SECRET_KEY=your-secure-random-key-here
   ```

6. **Generate Backend Domain**:
   - Click on backend service → "Settings" → "Networking"
   - Click "Generate Domain"
   - Copy the URL (e.g., `aiseo-backend-production.up.railway.app`)

7. **Deploy Frontend**:
   - Click "New" → "GitHub Repo"
   - Select same repository
   - Set **Root Directory**: `frontend`
   - Railway will use the `frontend/railway.json` config automatically

8. **Configure Frontend Environment Variables**:
   - Click on frontend service → "Variables"
   - Add:
   ```
   VITE_API_BASE_URL=https://YOUR_BACKEND_URL.up.railway.app/api
   NODE_ENV=production
   ```

9. **Generate Frontend Domain**:
   - Click on frontend service → "Settings" → "Networking"
   - Click "Generate Domain"

10. **Update Backend CORS** (Important!):
    - Go back to backend service → "Variables"
    - Update `CORS_ORIGINS` with actual frontend URL:
    ```
    CORS_ORIGINS=https://YOUR_FRONTEND_URL.up.railway.app,http://localhost:5173
    ```

---

### Option 2: Railway CLI Deploy

If you have the Railway CLI installed and logged in:

```bash
# Login first (opens browser)
railway login

# Initialize project
cd /path/to/aiseo
railway init --name aiseo

# Deploy backend
cd backend
railway link
railway add --database postgres
railway variables set CORS_ORIGINS="https://aiseo-frontend.up.railway.app" LOG_LEVEL="INFO" DEBUG="false"
railway up
railway domain  # Generate public URL

# Deploy frontend (new service in same project)
cd ../frontend
railway service --new --name aiseo-frontend
railway variables set VITE_API_BASE_URL="https://YOUR_BACKEND_URL.up.railway.app/api" NODE_ENV="production"
railway up
railway domain  # Generate public URL

# Update backend CORS with actual frontend URL
cd ../backend
railway variables set CORS_ORIGINS="https://YOUR_ACTUAL_FRONTEND_URL.up.railway.app,http://localhost:5173"
railway up
```

---

## Configuration Files

The following Railway config files are already set up:

### Backend (`backend/railway.json`)
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 30
  }
}
```

### Frontend (`frontend/railway.json`)
```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "npm install && npm run build"
  },
  "deploy": {
    "startCommand": "npx serve dist -s -l $PORT"
  }
}
```

---

## Environment Variables Reference

### Backend

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection (auto-set by Railway) | `postgresql://...` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `https://app.example.com` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `false` |
| `SECRET_KEY` | Session secret key | `random-32-char-string` |

### Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `https://api.example.com/api` |
| `NODE_ENV` | Node environment | `production` |

---

## Post-Deployment

### Verify Deployment

1. **Backend Health Check**: 
   ```
   curl https://YOUR_BACKEND_URL.up.railway.app/api/health
   ```
   Should return: `{"status": "healthy", "timestamp": "..."}`

2. **API Docs**: 
   ```
   https://YOUR_BACKEND_URL.up.railway.app/docs
   ```

3. **Admin Panel**:
   ```
   https://YOUR_BACKEND_URL.up.railway.app/admin
   ```

4. **Frontend Dashboard**:
   ```
   https://YOUR_FRONTEND_URL.up.railway.app
   ```

### Seed Initial Data

The backend automatically seeds initial brand data on startup. To add more data, use the admin panel or API endpoints.

---

## Troubleshooting

### Build Fails
- Check Railway logs for errors
- Ensure `requirements.txt` has all dependencies
- Verify Dockerfile builds locally: `docker build -t aiseo-backend ./backend`

### CORS Errors
- Verify `CORS_ORIGINS` includes your frontend URL
- Make sure URLs don't have trailing slashes
- Redeploy backend after changing CORS

### Database Connection Issues
- Ensure PostgreSQL addon is added
- `DATABASE_URL` should be auto-set by Railway
- Check database is running in Railway dashboard

### Frontend API Calls Fail
- Verify `VITE_API_BASE_URL` is correct
- Must include `/api` suffix
- Redeploy frontend after changing env vars

---

## Cost Estimate

Railway's free tier includes:
- $5 credit/month (enough for light usage)
- 500MB RAM per service
- Shared CPU

For production, consider upgrading to:
- Hobby Plan: $5/month per service
- Pro Plan: Usage-based pricing

---

## Alternative: Keep Frontend on Vercel

If you already have the frontend on Vercel, you can just deploy the backend to Railway:

1. Deploy backend to Railway (steps 3-6 above)
2. Update Vercel environment variable:
   - Go to Vercel dashboard → Project Settings → Environment Variables
   - Set `VITE_API_BASE_URL=https://YOUR_RAILWAY_BACKEND.up.railway.app/api`
   - Redeploy on Vercel

This gives you:
- **Vercel**: Optimized for static frontend (faster CDN)
- **Railway**: Great for backend APIs with database
