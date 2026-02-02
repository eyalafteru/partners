#!/bin/bash
# PartnerCalc OS - Deploy Script
# Run this to update the application after git push

set -e

echo "=================================================="
echo "  PartnerCalc OS - Deploy Update"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_DIR="/opt/partnercalc"
cd $APP_DIR

echo -e "${YELLOW}[1/4] Pulling latest code...${NC}"
git pull origin main

echo -e "${YELLOW}[2/4] Rebuilding containers...${NC}"
cd $APP_DIR/docker
docker compose -f docker-compose.prod.yml build --no-cache

echo -e "${YELLOW}[3/4] Restarting services...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo -e "${YELLOW}[4/4] Cleaning up old images...${NC}"
docker image prune -f

echo ""
echo -e "${GREEN}Deploy complete!${NC}"
echo ""
echo "Check status: docker compose -f docker-compose.prod.yml ps"
echo "View logs:    docker compose -f docker-compose.prod.yml logs -f"
