# Cloudflare Configuration for tokenspender.com

This guide connects all your services under tokenspender.com using Cloudflare.

## Architecture

```
                        Cloudflare DNS
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
app.tokenspender.com  api.tokenspender.com  vpn.tokenspender.com
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ Railway │         │ Railway │         │ Hetzner │
   │Frontend │         │ Backend │         │  VPN    │
   └─────────┘         └─────────┘         └─────────┘
```

## Step 1: Add DNS Records in Cloudflare

Go to https://dash.cloudflare.com/ → tokenspender.com → **DNS** → **Records**

### Railway Services (CNAME Records) - Proxied ✅

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| CNAME | `app` | `7c2nyb4u.up.railway.app` | ✅ Proxied (orange) |
| CNAME | `api` | `pwjhnfjb.up.railway.app` | ✅ Proxied (orange) |
| CNAME | `admin` | `dcuraqx4.up.railway.app` | ✅ Proxied (orange) |
| CNAME | `tester` | `1e3nu0es.up.railway.app` | ✅ Proxied (orange) |

### Hetzner VPN Server (A Records) - DNS Only ⚪

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `vpn` | `65.108.158.17` | ❌ DNS only (grey) |
| A | `scraper` | `65.108.158.17` | ❌ DNS only (grey) |

**Note**: VPN/Scraper should be "DNS Only" (grey cloud) because:
- They use non-HTTP ports (8001-8008)
- Cloudflare proxy only works for HTTP/HTTPS

## Step 3: SSL/TLS Settings

Go to **SSL/TLS > Overview**:
- Set mode to **Full (strict)**

Go to **SSL/TLS > Edge Certificates**:
- Enable **Always Use HTTPS**
- Enable **Automatic HTTPS Rewrites**

## Step 4: Configure Railway Custom Domains

### Frontend (app.yourdomain.com)

1. Go to Railway Dashboard > aiseo-frontend > Settings > Networking
2. Click "Custom Domain"
3. Enter: `app.yourdomain.com`
4. Railway will show you a CNAME target - use that in Cloudflare

### Backend API (api.yourdomain.com)

1. Go to Railway Dashboard > aiseo-api > Settings > Networking
2. Click "Custom Domain"
3. Enter: `api.yourdomain.com`

### Admin Dashboard (admin.yourdomain.com)

1. Go to Railway Dashboard > admin-dashboard > Settings > Networking
2. Click "Custom Domain"
3. Enter: `admin.yourdomain.com`

## Step 5: Update Environment Variables

### Railway Backend - Update CORS

Go to Railway > aiseo-api > Variables:

```
CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com,http://localhost:5173
```

### Railway Frontend - Update API URL

Go to Railway > aiseo-frontend > Variables:

```
VITE_API_BASE_URL=https://api.yourdomain.com/api
```

Then redeploy the frontend.

## Step 6: Cloudflare Page Rules (Optional)

Go to **Rules > Page Rules**:

### Cache API Responses
- URL: `api.yourdomain.com/api/health*`
- Setting: Cache Level = Bypass

### Security for Admin
- URL: `admin.yourdomain.com/*`
- Setting: Security Level = High

## Final URLs

After setup, your services will be available at:

| Service | URL |
|---------|-----|
| Frontend Dashboard | https://app.yourdomain.com |
| Backend API | https://api.yourdomain.com |
| API Documentation | https://api.yourdomain.com/docs |
| Admin Panel | https://api.yourdomain.com/admin |
| Admin Dashboard | https://admin.yourdomain.com |
| API Tester | https://tester.yourdomain.com |
| VPN Dashboard | http://vpn.yourdomain.com:9090 |
| Scraper API | http://scraper.yourdomain.com:5000 |

## Troubleshooting

### SSL Certificate Errors
- Wait 15-30 minutes for Cloudflare to provision certificates
- Ensure SSL mode is "Full (strict)"
- Check Railway shows the custom domain as "verified"

### CORS Errors
- Update CORS_ORIGINS in Railway backend
- Redeploy after changing environment variables
- Check browser console for exact error

### VPN Ports Not Accessible
- VPN records must be "DNS Only" (grey cloud)
- Cloudflare proxy doesn't support non-HTTP ports
- Access via: `http://vpn.yourdomain.com:9090`
