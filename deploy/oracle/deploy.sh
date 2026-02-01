#!/bin/bash
# Oracle Cloud VPN Deployment Script
# For ARM (Ampere A1) FREE TIER instances

set -e

SERVER_IP="${1:-}"
SSH_KEY="${2:-~/.ssh/id_rsa}"
SSH_USER="${3:-ubuntu}"  # Oracle uses 'ubuntu' for Ubuntu images

if [ -z "$SERVER_IP" ]; then
    echo "Usage: $0 <SERVER_IP> [SSH_KEY_PATH] [SSH_USER]"
    echo "Example: $0 123.45.67.89 ~/.ssh/oracle ubuntu"
    exit 1
fi

echo "🚀 Deploying AiSEO VPN Stack to Oracle Cloud ($SERVER_IP)"
echo "=========================================================="

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
PROTONVPN_KEY_FR=
PROTONVPN_KEY_DE=
PROTONVPN_KEY_NL=
PROTONVPN_KEY_IT=
PROTONVPN_KEY_ES=
PROTONVPN_KEY_UK=
PROTONVPN_KEY_CH=
PROTONVPN_KEY_SE=

# Bright Data (optional)
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

mkdir -p "$DEPLOY_DIR/data/screenshots"

echo "📤 Uploading to server..."
rsync -avz --progress -e "ssh -i $SSH_KEY" "$DEPLOY_DIR/" "$SSH_USER@$SERVER_IP:/opt/aiseo/"

echo "🔧 Configuring Oracle Cloud firewall..."
ssh -i "$SSH_KEY" "$SSH_USER@$SERVER_IP" << 'REMOTE_SCRIPT'
cd /opt/aiseo

# Oracle Cloud specific: Open iptables ports
sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 9090 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 8001:8008 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 8101:8108 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 9001:9008 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || sudo iptables-save | sudo tee /etc/iptables/rules.v4

# Ensure Docker is running
sudo systemctl enable docker
sudo systemctl start docker

# Create data directories
mkdir -p data/screenshots
chmod 600 .env

echo ""
echo "✅ Files uploaded successfully!"
echo ""
echo "⚠️  IMPORTANT ORACLE CLOUD STEPS:"
echo ""
echo "1. Edit .env with your ProtonVPN keys:"
echo "   nano /opt/aiseo/.env"
echo ""
echo "2. Open ports in Oracle Cloud Console:"
echo "   - Go to: Networking > Virtual Cloud Networks > Your VCN > Security Lists"
echo "   - Add Ingress Rules for ports: 5000, 9090, 8001-8008, 8101-8108, 9001-9008"
echo ""
echo "3. Start the VPN stack:"
echo "   cd /opt/aiseo && sudo docker-compose up -d"
echo ""
REMOTE_SCRIPT

rm -rf "$DEPLOY_DIR"

echo ""
echo "🎉 Deployment complete!"
echo "========================"
echo ""
echo "⚠️  IMPORTANT: Oracle Cloud requires TWO firewall configs:"
echo ""
echo "1. Instance iptables (done automatically)"
echo "2. VCN Security List (do manually in Oracle Console):"
echo "   - Login to Oracle Cloud Console"
echo "   - Go to Networking > Virtual Cloud Networks"
echo "   - Select your VCN > Security Lists > Default"
echo "   - Add Ingress Rules:"
echo "     - Source: 0.0.0.0/0, Protocol: TCP, Port: 5000"
echo "     - Source: 0.0.0.0/0, Protocol: TCP, Port: 9090"
echo "     - Source: 0.0.0.0/0, Protocol: TCP, Port: 8001-8008"
echo ""
echo "Next steps:"
echo "1. SSH: ssh -i $SSH_KEY $SSH_USER@$SERVER_IP"
echo "2. Edit: nano /opt/aiseo/.env"
echo "3. Start: cd /opt/aiseo && sudo docker-compose up -d"
