#!/bin/bash
# PartnerCalc OS - Server Setup Script
# Run on a fresh Ubuntu 24.04 server

set -e  # Exit on any error

echo "=================================================="
echo "  PartnerCalc OS - Server Setup"
echo "  Ubuntu 24.04"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="partners.ppcmedia.co.il"
APP_DIR="/opt/partnercalc"
GITHUB_REPO="https://github.com/YOUR_USERNAME/partnercalc-os.git"  # Change this!

echo -e "${YELLOW}[1/8] Updating system...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}[2/8] Installing required packages...${NC}"
apt install -y \
    curl \
    wget \
    git \
    openssl \
    ca-certificates \
    gnupg \
    lsb-release

echo -e "${YELLOW}[3/8] Installing Docker...${NC}"
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify Docker installation
docker --version
docker compose version

echo -e "${YELLOW}[4/8] Configuring hosts file...${NC}"
# Add domain to hosts file (for local resolution without DNS)
if ! grep -q "$DOMAIN" /etc/hosts; then
    echo "127.0.0.1 $DOMAIN" >> /etc/hosts
    echo -e "${GREEN}Added $DOMAIN to /etc/hosts${NC}"
fi

echo -e "${YELLOW}[5/8] Creating SSL certificates...${NC}"
# Create self-signed SSL certificate
mkdir -p /etc/ssl/private
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt \
    -subj "/CN=$DOMAIN"

echo -e "${GREEN}Self-signed SSL certificate created${NC}"

echo -e "${YELLOW}[6/8] Cloning repository...${NC}"
# Create app directory
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or update repository
if [ -d ".git" ]; then
    echo "Repository exists, pulling latest..."
    git pull
else
    echo "Cloning repository..."
    git clone $GITHUB_REPO .
fi

echo -e "${YELLOW}[7/8] Setting up environment...${NC}"
# Create .env file from example if it doesn't exist
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/env.example.txt" ]; then
        cp backend/env.example.txt backend/.env
        echo -e "${YELLOW}Created backend/.env from template${NC}"
        echo -e "${RED}IMPORTANT: Edit backend/.env with your API keys!${NC}"
    fi
fi

echo -e "${YELLOW}[8/8] Starting Docker containers...${NC}"
cd $APP_DIR/docker

# Build and start all containers
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "=================================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "   nano $APP_DIR/backend/.env"
echo ""
echo "2. Restart containers after editing .env:"
echo "   cd $APP_DIR/docker"
echo "   docker compose -f docker-compose.prod.yml restart"
echo ""
echo "3. Check container status:"
echo "   docker compose -f docker-compose.prod.yml ps"
echo ""
echo "4. View logs:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "5. Access the app:"
echo "   https://$DOMAIN"
echo ""
echo "6. For local testing, add to your computer's hosts file:"
echo "   $(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP') $DOMAIN"
echo ""
