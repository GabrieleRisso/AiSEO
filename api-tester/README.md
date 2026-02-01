# API Tester - Postman-like Web Interface

A web-based API testing interface for the AiSEO project, similar to Postman. Test your APIs graphically and view logs from Docker containers.

## Features

- **API Testing**: Test all endpoints from both the Scraper API (port 5000) and Backend API (port 8000)
- **Request Builder**: Build requests with different HTTP methods, query parameters, and JSON bodies
- **Response Viewer**: View formatted JSON responses with status codes and timing
- **Log Viewer**: View real-time logs from Docker containers
- **Pre-configured Endpoints**: Click endpoints in the sidebar to quickly test common API calls
- **Postman Integration**: Download Postman collection and environment files directly from the interface

## Usage

### Starting the Service

The API tester is included in `docker-compose.yml`. To start it:

```bash
docker-compose up -d api-tester
```

Or start all services:

```bash
docker-compose up -d
```

### Accessing the Interface

Open your browser and navigate to:

```
http://localhost:9000
```

### Using the Interface

1. **Select an Endpoint**: Click any endpoint in the left sidebar to load it into the request builder
2. **Modify Request**: 
   - Change the HTTP method if needed
   - Add query parameters using the "Add Parameter" button
   - Edit the JSON body in the request body editor
3. **Send Request**: Click the "Send" button to execute the request
4. **View Response**: The response tab will show the status code, timing, and formatted JSON
5. **View Logs**: Switch to the Logs tab to view container logs. Select a container and click Refresh

## Available Endpoints

### Scraper API (Port 5000)
- `GET /health` - Health check
- `GET /config` - Get scraper configuration
- `POST /scrape` - Execute a scraping job

### Backend API (Port 8000)
- `GET /api/health` - Health check
- `GET /api/config` - Get system configuration
- `GET /api/vpn/servers` - Get VPN server list
- `GET /api/brands` - List all brands
- `GET /api/brands/details` - Get detailed brand analytics
- `POST /api/brands` - Create a new brand
- `GET /api/prompts` - List all prompts
- `GET /api/sources` - List all sources
- `GET /api/metrics` - Get dashboard metrics
- `GET /api/visibility` - Get visibility data
- `GET /api/sources/analytics` - Get source analytics
- `GET /api/suggestions` - Get SEO suggestions
- `GET /api/jobs` - List all jobs
- `POST /api/jobs/scrape` - Create a scraping job

## Logs

The log viewer can display logs from any Docker container in your setup:
- `aiseo-scraper` - Scraper service logs
- `aiseo-api` - Backend API logs
- `vpn-fr`, `vpn-de`, `vpn-nl`, etc. - VPN container logs
- `vpn-manager` - VPN manager logs

Logs are color-coded:
- **Red**: Errors
- **Yellow**: Warnings
- **Green**: Info messages
- **Gray**: Debug messages

## Development

### Running Locally

```bash
cd api-tester
pip install -r requirements.txt
python server.py
```

### Building the Docker Image

```bash
docker build -t aiseo-api-tester ./api-tester
```

## Postman Collection

The API Tester includes Postman collection files:

- **Download Collection**: Click "Download Postman Collection" button in the sidebar
- **Download Environment**: Click "Download Environment" button in the sidebar
- **Direct URLs**: 
  - Collection: http://localhost:9000/postman/collection
  - Environment: http://localhost:9000/postman/environment

See [POSTMAN.md](./POSTMAN.md) for detailed Postman setup instructions.

## Notes

- The log viewer requires Docker socket access to fetch container logs
- Make sure Docker is running and the containers are accessible
- The interface uses CORS, so API endpoints must allow requests from `http://localhost:9000`
