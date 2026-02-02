"""Scrape all domains and save HTML content (no WHOIS)"""
import asyncio
import sqlite3
import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def scrape_url(url: str) -> dict:
    """Scrape single URL"""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return {"error": f"Status {response.status_code}"}
            
            html = response.text
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Get title
            title = ""
            if soup.title:
                title = soup.title.string or ""
            
            # Get clean text
            inner_text = ""
            if soup.body:
                for element in soup.body(['script', 'style', 'noscript']):
                    element.decompose()
                inner_text = soup.body.get_text(separator=' ', strip=True)[:10000]
            
            return {
                "title": title[:500],
                "html_body": html[:50000],
                "html_text": inner_text[:10000],
                "error": None
            }
            
    except Exception as e:
        return {"error": str(e)}

async def main():
    conn = sqlite3.connect('partnercalc.db')
    c = conn.cursor()
    
    # Get all pending domains
    c.execute("SELECT id, url, domain FROM scan_queue WHERE status = 'pending'")
    rows = c.fetchall()
    
    print(f"Found {len(rows)} domains to scrape")
    
    for i, (row_id, url, domain) in enumerate(rows):
        print(f"[{i+1}/{len(rows)}] Scraping {domain}...")
        
        result = await scrape_url(url)
        
        if result.get("error"):
            print(f"  ❌ Error: {result['error'][:50]}")
            c.execute("""
                UPDATE scan_queue 
                SET status = 'error', error_message = ?
                WHERE id = ?
            """, (result['error'][:500], row_id))
        else:
            print(f"  ✅ Got {len(result.get('html_text', ''))} chars")
            c.execute("""
                UPDATE scan_queue 
                SET html_body = ?, html_text = ?, title = COALESCE(title, ?), status = 'matched'
                WHERE id = ?
            """, (result['html_body'], result['html_text'], result['title'], row_id))
        
        conn.commit()
        
        # Small delay to be nice
        await asyncio.sleep(0.5)
    
    conn.close()
    print(f"\nDone! Scraped {len(rows)} domains")

if __name__ == "__main__":
    asyncio.run(main())
