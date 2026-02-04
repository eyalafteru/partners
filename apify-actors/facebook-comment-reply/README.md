# Facebook Comment Reply Actor

Apify Actor for replying to comments on Facebook posts using Playwright browser automation.

## ⚠️ Important Notes

1. **Facebook Terms of Service**: This actor automates Facebook interactions. Use responsibly and be aware of Facebook's ToS.
2. **Cookie Expiration**: Facebook session cookies expire. Refresh them regularly.
3. **Rate Limiting**: Use delays between actions to avoid detection.
4. **DOM Changes**: Facebook frequently updates their DOM structure. Selectors may need updates.

## Input

```json
{
    "postUrl": "https://www.facebook.com/groups/123/posts/456",
    "commentId": "optional_comment_id_to_reply_to",
    "replyMessage": "Your reply message here",
    "cookies": [
        {
            "name": "c_user",
            "value": "your_user_id",
            "domain": ".facebook.com"
        },
        {
            "name": "xs",
            "value": "your_session_token",
            "domain": ".facebook.com"
        }
    ],
    "proxyConfiguration": {
        "useApifyProxy": true
    }
}
```

## Output

```json
{
    "success": true,
    "commentId": "new_comment_id",
    "screenshotUrl": "screenshot_timestamp.png"
}
```

## Getting Facebook Cookies

1. Log into Facebook in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies → facebook.com
4. Copy the following cookies: `c_user`, `xs`, `datr`, `fr`

Or use a browser extension like "EditThisCookie" to export all cookies as JSON.

## Development

```bash
# Install dependencies
npm install

# Run locally
apify-ts run

# Deploy to Apify
apify push
```

## Safety Measures

- Random delays between actions (1-5 seconds)
- Human-like typing simulation
- Realistic browser fingerprint
- Proxy support for IP rotation
- Session validation before actions

## Troubleshooting

- **"Not logged in"**: Cookies are expired, get new ones
- **"Could not find comment input"**: Facebook DOM changed, update selectors
- **Timeout errors**: Try with a proxy, increase timeout values
