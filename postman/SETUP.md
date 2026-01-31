# Postman Setup Guide

This guide will help you set up and use the Postman collection for testing the AiSEO APIs.

## Prerequisites

- [Postman](https://www.postman.com/downloads/) installed (Desktop or Web)
- Docker services running (see main README)
- Git repository cloned

## Quick Setup (5 minutes)

### Step 1: Import Collection

1. Open Postman
2. Click **Import** (top left corner)
3. Click **Upload Files**
4. Navigate to `postman/AiSEO_API.postman_collection.json`
5. Click **Import**

### Step 2: Import Environment

1. Click the **Environments** icon in the left sidebar (or press `Ctrl+E`)
2. Click **Import**
3. Select `postman/Local.postman_environment.json`
4. Click **Import**
5. Select **Local** from the environment dropdown (top right)

### Step 3: Verify Setup

1. Expand **AiSEO API Collection** → **Scraper API** → **Health Check**
2. Click **Send**
3. You should see:
   - Status: `200 OK`
   - Response: `{"status": "ok"}`

✅ **Setup Complete!**

## GitHub Integration

### Option 1: Manual Sync (Recommended for Teams)

1. **Export Collection**
   - Right-click collection → **Export**
   - Choose **Collection v2.1**
   - Save to `postman/AiSEO_API.postman_collection.json`
   - Commit and push to GitHub

2. **Export Environment**
   - Right-click environment → **Export**
   - Save to `postman/Local.postman_environment.json`
   - Commit and push to GitHub

3. **Team Members Import**
   - Pull latest changes
   - Import updated collection/environment
   - Overwrite existing if prompted

### Option 2: Postman Cloud Sync (Advanced)

1. **Create Postman Account**
   - Sign up at [postman.com](https://www.postman.com)
   - Create a workspace

2. **Sync Collection**
   - In Postman, click **Sync** (top right)
   - Sign in to Postman account
   - Collection will sync to cloud

3. **Share with Team**
   - Invite team members to workspace
   - They can sync collection automatically

4. **GitHub Integration** (Optional)
   - Connect Postman workspace to GitHub
   - Collections sync automatically on push
   - See [Postman Docs](https://learning.postman.com/docs/integrations/available-integrations/github/)

## Testing Workflows

### Basic API Test

1. **Scraper API Health**
   - `Scraper API` → `Health Check` → **Send**
   - Should return `200 OK`

2. **Backend API Health**
   - `Backend API` → `System` → `Health Check` → **Send**
   - Should return `200 OK`

### Complete Scraping Workflow

1. **Create Scrape Job**
   - `Backend API` → `Jobs` → `Create Scrape Job (One-time)`
   - Modify query: `"best seo tools"`
   - Click **Send**
   - Note the `job_id` in response

2. **Check Job Status**
   - `Backend API` → `Jobs` → `List Jobs`
   - Add query param: `status=completed`
   - Click **Send**
   - Find your job in the list

3. **View Results**
   - `Backend API` → `Prompts` → `List Prompts`
   - Click **Send**
   - Find your query in results

### Brand Management Workflow

1. **List Brands**
   - `Backend API` → `Brands` → `List Brands` → **Send**
   - See all brands with visibility metrics

2. **Create Brand**
   - `Backend API` → `Brands` → `Create Brand`
   - Modify brand details:
     ```json
     {
       "id": "my-brand",
       "name": "My Brand",
       "type": "competitor",
       "color": "#ff5733",
       "variations": ["My Brand", "MB"]
     }
     ```
   - Click **Send**
   - Brand ID saved automatically to `last_brand_id`

3. **Verify Brand**
   - `Backend API` → `Brands` → `List Brands` → **Send**
   - Your brand should appear in the list

4. **Delete Brand** (Optional)
   - `Backend API` → `Brands` → `Delete Brand` → **Send**
   - Uses `{{last_brand_id}}` automatically

## Environment Variables

The collection uses these variables (set in environment):

| Variable | Default | Description |
|----------|---------|-------------|
| `scraper_base_url` | `http://localhost:5000` | Scraper API base URL |
| `backend_base_url` | `http://localhost:8000` | Backend API base URL |
| `last_job_id` | (auto-set) | Last created job ID |
| `last_brand_id` | (auto-set) | Last created brand ID |

### Creating Custom Environments

1. Click **Environments** → **+**
2. Name it (e.g., "Production")
3. Add variables:
   - `scraper_base_url`: `https://api.yourdomain.com:5000`
   - `backend_base_url`: `https://api.yourdomain.com:8000`
4. Save
5. Select environment from dropdown

## Automated Tests

Most requests include automated tests. To view:

1. Send a request
2. Click **Test Results** tab
3. See test results:
   - ✓ Status code checks
   - ✓ Response structure validation
   - ✓ Required fields verification

### Running All Tests

1. Select collection folder
2. Click **Run** button (top right)
3. Click **Run AiSEO API Collection**
4. Review test results

## Troubleshooting

### "Connection Refused"

**Problem**: Cannot connect to API

**Solutions**:
1. Check services are running:
   ```bash
   docker-compose ps
   ```
2. Verify ports:
   ```bash
   curl http://localhost:5000/health
   curl http://localhost:8000/api/health
   ```
3. Check environment variables are set correctly

### Tests Failing

**Problem**: Automated tests fail

**Solutions**:
1. Check response structure matches expected format
2. Verify data exists in database
3. Review test scripts in **Tests** tab
4. Check console for errors

### CORS Errors

**Problem**: CORS errors in browser console

**Solutions**:
1. Use Postman Desktop (not browser)
2. Check `CORS_ORIGINS` environment variable
3. Verify backend CORS middleware is configured

### Environment Variables Not Working

**Problem**: Variables like `{{scraper_base_url}}` not resolving

**Solutions**:
1. Ensure environment is selected (top right dropdown)
2. Check variable names match exactly (case-sensitive)
3. Verify environment is imported correctly
4. Try typing `{{` to see autocomplete suggestions

## Best Practices

### 1. Use Environments
- Create separate environments for dev/staging/prod
- Never commit sensitive data to environment files
- Use `.gitignore` for personal environments

### 2. Organize Requests
- Use folders to group related endpoints
- Name requests descriptively
- Add descriptions to requests

### 3. Write Tests
- Add tests for all critical endpoints
- Test both success and error cases
- Use tests to validate data structure

### 4. Document Changes
- Update collection when adding endpoints
- Add descriptions to new requests
- Update README when structure changes

### 5. Version Control
- Commit collection changes regularly
- Use meaningful commit messages
- Review changes before merging

## Advanced Features

### Pre-request Scripts

Add scripts that run before requests:

```javascript
// Set dynamic timestamp
pm.environment.set("timestamp", new Date().toISOString());

// Generate random query
pm.environment.set("random_query", "test-" + Math.random());
```

### Test Scripts

Add custom validations:

```javascript
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(5000);
});

pm.test("Custom validation", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.customField).to.equal("expected");
});
```

### Collection Variables

Set variables at collection level:

1. Right-click collection → **Edit**
2. Go to **Variables** tab
3. Add variables accessible to all requests

### Chaining Requests

Use saved variables to chain requests:

1. First request saves ID:
   ```javascript
   pm.environment.set("job_id", pm.response.json().job_id);
   ```

2. Second request uses ID:
   ```
   {{backend_base_url}}/api/jobs/{{job_id}}
   ```

## Resources

- [Postman Learning Center](https://learning.postman.com/)
- [API Documentation](../API_DOCS.md)
- [Project README](../README.md)
- [Collection README](./README.md)

## Support

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [API Documentation](../API_DOCS.md)
3. Check service logs:
   ```bash
   docker-compose logs scraper
   docker-compose logs backend
   ```
4. Validate collection:
   ```bash
   cd postman
   ./validate.sh
   ```
