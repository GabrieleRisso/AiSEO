#!/bin/bash

# AiSEO Railway Deployment Script
# This script deploys both backend and frontend to Railway

set -e

RAILWAY="/usr/local/bin/railway"

echo "🚀 AiSEO Railway Deployment"
echo "==========================="
echo ""

# Check if railway CLI is installed
if ! command -v $RAILWAY &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    curl -fsSL https://railway.app/install.sh | sh
    RAILWAY="/usr/local/bin/railway"
fi

# Check if logged in
if ! $RAILWAY whoami &> /dev/null; then
    echo "📝 Please login to Railway first:"
    $RAILWAY login
fi

echo ""
echo "Step 1: Creating Railway Project"
echo "---------------------------------"

# Initialize project if not already done
if [ ! -f ".railway/project.json" ]; then
    echo "Creating new Railway project..."
    $RAILWAY init --name aiseo
else
    echo "Railway project already initialized."
fi

echo ""
echo "Step 2: Deploying Backend (with PostgreSQL)"
echo "--------------------------------------------"

# Deploy backend
cd backend

# Link to the project
$RAILWAY link

# Add PostgreSQL addon
echo "Adding PostgreSQL database..."
$RAILWAY add --database postgres || echo "PostgreSQL may already exist"

# Set environment variables
echo "Setting environment variables..."
$RAILWAY variables set CORS_ORIGINS="https://aiseo-frontend.up.railway.app,http://localhost:5173"
$RAILWAY variables set LOG_LEVEL="INFO"
$RAILWAY variables set DEBUG="false"
$RAILWAY variables set SECRET_KEY="$(openssl rand -hex 32)"

# Deploy backend
echo "Deploying backend..."
$RAILWAY up --detach

# Get backend URL
BACKEND_URL=$($RAILWAY domain 2>/dev/null || echo "")
if [ -z "$BACKEND_URL" ]; then
    echo "Generating backend domain..."
    $RAILWAY domain
    BACKEND_URL=$($RAILWAY domain)
fi

echo "✅ Backend deployed at: https://$BACKEND_URL"

cd ..

echo ""
echo "Step 3: Deploying Frontend"
echo "--------------------------"

cd frontend

# Create a new service in the same project for frontend
$RAILWAY service --new --name aiseo-frontend || echo "Frontend service may already exist"

# Set frontend environment variables
echo "Setting frontend environment variables..."
$RAILWAY variables set VITE_API_BASE_URL="https://$BACKEND_URL/api"
$RAILWAY variables set NODE_ENV="production"

# Deploy frontend
echo "Deploying frontend..."
$RAILWAY up --detach

# Get frontend URL
FRONTEND_URL=$($RAILWAY domain 2>/dev/null || echo "")
if [ -z "$FRONTEND_URL" ]; then
    echo "Generating frontend domain..."
    $RAILWAY domain
    FRONTEND_URL=$($RAILWAY domain)
fi

echo "✅ Frontend deployed at: https://$FRONTEND_URL"

cd ..

echo ""
echo "Step 4: Update CORS for Frontend URL"
echo "-------------------------------------"

cd backend
$RAILWAY variables set CORS_ORIGINS="https://$FRONTEND_URL,http://localhost:5173"
$RAILWAY up --detach
cd ..

echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "📦 Backend API:  https://$BACKEND_URL"
echo "🖥️  Frontend:     https://$FRONTEND_URL"
echo "📊 Admin Panel:  https://$BACKEND_URL/admin"
echo "📚 API Docs:     https://$BACKEND_URL/docs"
echo ""
echo "⚠️  Note: It may take a few minutes for the services to fully start."
echo "    Check status with: $RAILWAY status"
