#!/usr/bin/env python3
"""Test WhatsApp Green API"""
import httpx
import asyncio

API_URL = "https://7105.api.greenapi.com"
INSTANCE_ID = "7105206891"
API_TOKEN = "20fdcb013dd3423e845cba372e6886996bf7246ed39d4b9c89"
PHONE = "972509543601"

async def test():
    url = f"{API_URL}/waInstance{INSTANCE_ID}/sendMessage/{API_TOKEN}"
    payload = {
        "chatId": f"{PHONE}@c.us",
        "message": "🔔 Test from PartnerCalc - WhatsApp notifications work!"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test())
