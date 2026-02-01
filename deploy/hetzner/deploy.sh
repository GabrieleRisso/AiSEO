#!/bin/bash
# Hetzner VPN Deployment Script
# Run this AFTER creating the server with cloud-init

set -e

SERVER_IP="${1:-}"
SSH_KEY="${2:-~/.ssh/id_rsa}"

if [ -z "$SERVER_IP" ]; then
    echo "Usage: $0 <SERVER_IP> [SSH_KEY_PATH]"
    echo "Example: $0 123.45.67.89 ~/.ssh/hetzner"
    exit 1
fi

echo "🚀 Deploying AiSEO VPN Stack to Hetzner ($SERVER_IP)"
echo "======================================================"

# Create deployment package
echo "📦 Creating deployment package..."
DEPLOY_DIR=$(mktemp -d)
cp -r ../docker-compose.vpn.yml "$DEPLOY_DIR/docker-compose.yml"
cp -r ../../Dockerfile.scraper "$DEPLOY_DIR/"
cp -r ../../src "$DEPLOY_DIR/"
cp -r ../../scripts "$DEPLOY_DIR/"
cp -r ../../config "$DEPLOY_DIR/" 2>/dev/null || mkdir -p "$DEPLOY_DIR/config"
cp -r ../../vpn-dashboard "$DEPLOY_DIR/"
cp ../../pyproject.toml "$DEPLOY_DIR/" 2>/dev/null || true

# Create .env template
cat > "$DEPLOY_DIR/.env" << 'EOF'
# ProtonVPN WireGuard Keys
# Generate from: https://account.protonvpn.com/downloads#wireguard-configuration
PROTONVPN_KEY_FR=
PROTONVPN_KEY_DE=
PROTONVPN_KEY_NL=
PROTONVPN_KEY_IT=
PROTONVPN_KEY_ES=
PROTONVPN_KEY_UK=
PROTONVPN_KEY_CH=
PROTONVPN_KEY_SE=

# Bright Data Residential Proxy (optional - leave empty to skip)
BRIGHT_DATA_USER=
BRIGHT_DATA_PASSWORD=
BRIGHT_DATA_HOST=brd.superproxy.io
BRIGHT_DATA_PORT=22225

# Bright Data Scraping Browser (optional)
BRIGHTDATA_API_TOKEN=
BRIGHTDATA_CUSTOMER_ID=
BRIGHTDATA_BROWSER_ZONE=scraping_browser1
BRIGHTDATA_BROWSER_PASSWORD=
EOF

# Create data directories
mkdir -p "$DEPLOY_DIR/data/screenshots"

echo "📤 Uploading to server..."
rsync -avz --progress -e "ssh -i $SSH_KEY" "$DEPLOY_DIR/" "root@$SERVER_IP:/opt/aiseo/"

echo "🔧 Setting up server..."
ssh -i "$SSH_KEY" "root@$SERVER_IP" << 'REMOTE_SCRIPT'
cd /opt/aiseo

# Ensure Docker is running
systemctl enable docker
systemctl start docker

# Create data directories
mkdir -p data/screenshots

# Set permissions
chmod 600 .env

echo ""
echo "✅ Files uploaded successfully!"
echo ""
echo "⚠️  IMPORTANT: Edit /opt/aiseo/.env with your ProtonVPN keys!"
echo "   nano /opt/aiseo/.env"
echo ""
echo "Then start the VPN stack:"
echo "   cd /opt/aiseo && docker-compose up -d"
echo ""
REMOTE_SCRIPT

# Cleanup
rm -rf "$DEPLOY_DIR"

echo ""
echo "🎉 Deployment complete!"
echo "========================"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh -i $SSH_KEY root@$SERVER_IP"
echo "2. Edit .env file: nano /opt/aiseo/.env"
echo "3. Start services: cd /opt/aiseo && docker-compose up -d"
echo "4. Check status: docker-compose ps"
echo ""
echo "Endpoints (after starting):"
echo "  - VPN Dashboard: http://$SERVER_IP:9090"
echo "  - Scraper API:   http://$SERVER_IP:5000"
echo "  - VPN Proxies:   http://$SERVER_IP:8001-8008"
