# OAuth Authentication Setup Guide

This guide walks you through setting up OAuth authentication for the WoW Guild Analytics MCP Server using Discord or Google as your identity provider.

## Overview

The MCP server supports OAuth 2.1 authentication using FastMCP's built-in OAuthProxy. This provides:

- Secure user authentication via Discord or Google
- Automatic OAuth flow handling (authorization, token exchange, refresh)
- Token encryption and secure storage
- PKCE support for enhanced security
- Protected resource metadata endpoints

## Supported Providers

- **Discord OAuth**: Authenticate users via their Discord accounts
- **Google OAuth**: Authenticate users via their Google accounts

## Quick Start

### 1. Choose Your Provider

Decide whether you want to use Discord or Google for authentication. You can only use one provider at a time.

### 2. Register Your Application

#### Discord Setup

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Give your application a name (e.g., "WoW Guild Analytics")
4. Go to the "OAuth2" section in the left sidebar
5. Click "Add Redirect" and enter:
   ```
   http://localhost:8000/oauth/callback
   ```
   For production, use your server's public URL:
   ```
   https://your-server.herokuapp.com/oauth/callback
   ```
6. Under "OAuth2 Scopes", select:
   - `identify` - Allows reading basic user info
   - `email` - Allows reading user email
7. Copy your **Client ID** and **Client Secret**

#### Google Setup

1. Go to https://console.cloud.google.com
2. Create a new project or select an existing one
3. Go to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Configure the OAuth consent screen if prompted:
   - User type: External
   - Add required information (app name, support email, etc.)
6. Create OAuth client:
   - Application type: Web application
   - Add authorized redirect URI:
     ```
     http://localhost:8000/oauth/callback
     ```
     For production:
     ```
     https://your-server.herokuapp.com/oauth/callback
     ```
7. Copy your **Client ID** and **Client Secret**

### 3. Configure Environment Variables

Create a `.env` file in your project root (or use the provided `.env.example` as a template):

#### For Discord Authentication

```bash
# Enable Discord OAuth
OAUTH_PROVIDER=discord

# Discord Credentials
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here

# Server Base URL
OAUTH_BASE_URL=http://localhost:8000
# For production: https://your-app.herokuapp.com
```

#### For Google Authentication

```bash
# Enable Google OAuth
OAUTH_PROVIDER=google

# Google Credentials
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Server Base URL
OAUTH_BASE_URL=http://localhost:8000
# For production: https://your-app.herokuapp.com
```

### 4. Start the Server

```bash
python -m app.mcp_server_fastmcp
```

You should see log messages indicating OAuth is enabled:

```
INFO - OAuth authentication enabled with provider: discord
INFO - OAuth base URL: http://localhost:8000
INFO - OAuth scopes: identify, email
```

### 5. Test Authentication

#### Option A: Test with MCP Inspector

1. Install MCP Inspector:
   ```bash
   npx @modelcontextprotocol/inspector
   ```

2. Connect to your server:
   ```
   http://localhost:8000/mcp
   ```

3. Follow the OAuth flow in your browser

#### Option B: Test with Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wow-guild": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Restart Claude Desktop and it will prompt you to authenticate.

## Production Deployment

### Heroku Deployment

1. Set environment variables:
   ```bash
   heroku config:set OAUTH_PROVIDER=discord
   heroku config:set DISCORD_CLIENT_ID=your_client_id
   heroku config:set DISCORD_CLIENT_SECRET=your_client_secret
   heroku config:set OAUTH_BASE_URL=https://your-app.herokuapp.com
   ```

2. Update OAuth redirect URI in Discord/Google console:
   ```
   https://your-app.herokuapp.com/oauth/callback
   ```

3. Deploy:
   ```bash
   git push heroku main
   ```

### Security Best Practices

1. **Always use HTTPS in production**: OAuth requires HTTPS for security
2. **Keep secrets secure**: Never commit `.env` files to git
3. **Use environment variables**: Store credentials in Heroku config vars or similar
4. **Rotate credentials regularly**: Periodically regenerate Client Secrets
5. **Limit OAuth scopes**: Only request the minimum required permissions

## Accessing User Information in Tools

You can access authenticated user information in your tool functions:

```python
from fastmcp import Context

@mcp.tool()
async def analyze_guild_performance(
    realm: str,
    guild_name: str,
    ctx: Context = None
) -> Dict[str, Any]:
    # Access authenticated user info
    if ctx and ctx.auth:
        user = ctx.auth.user
        user_id = user.get('id')
        email = user.get('email')
        logger.info(f"User {email} is analyzing guild {guild_name}")

    # Rest of your tool logic
    ...
```

## Disabling Authentication

To run the server without authentication:

1. Remove or comment out the `OAUTH_PROVIDER` environment variable:
   ```bash
   # OAUTH_PROVIDER=discord
   ```

2. Or set it to an empty string:
   ```bash
   OAUTH_PROVIDER=
   ```

3. Restart the server

The server will run in public mode without requiring authentication.

## Troubleshooting

### Error: "Discord/Google OAuth credentials not configured"

**Solution**: Ensure you have set the required environment variables:
- `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` for Discord
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` for Google

### Error: "Redirect URI mismatch"

**Solution**: Ensure the redirect URI in your OAuth provider console exactly matches:
```
{OAUTH_BASE_URL}/oauth/callback
```

### Error: "Invalid client"

**Solution**: Double-check your Client ID and Client Secret are correct and properly copied.

### OAuth flow redirects to wrong URL

**Solution**: Ensure `OAUTH_BASE_URL` is set to your server's public URL, not `localhost` in production.

### Users can't authenticate

**Checklist**:
1. Is HTTPS enabled in production?
2. Is the redirect URI correctly configured in the provider console?
3. Are all environment variables set correctly?
4. Check server logs for detailed error messages

## Technical Details

### What FastMCP Handles Automatically

FastMCP's OAuthProxy automatically handles:

- Authorization flow initiation
- Callback endpoint (`/oauth/callback`)
- Authorization code exchange for tokens
- Token encryption and secure storage
- Token refresh when expired
- PKCE (Proof Key for Code Exchange)
- Protected resource metadata endpoint (`/.well-known/oauth-protected-resource`)
- WWW-Authenticate headers on 401 responses
- Dynamic Client Registration support

### OAuth Endpoints

When authentication is enabled, the server exposes:

- `/.well-known/oauth-protected-resource` - OAuth metadata
- `/oauth/authorize` - Authorization endpoint (proxy)
- `/oauth/token` - Token endpoint (proxy)
- `/oauth/callback` - Callback handler (automatic)

### Scopes Requested

**Discord**:
- `identify` - Read user ID and username
- `email` - Read user email address

**Google**:
- `openid` - OpenID Connect authentication
- `email` - Read user email
- `profile` - Read user profile information

## Additional Resources

- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP OAuth Proxy](https://gofastmcp.com/servers/auth/oauth-proxy)
- [Discord OAuth2 Documentation](https://discord.com/developers/docs/topics/oauth2)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [MCP Specification - Authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

## Support

For issues or questions:
- Email: noah.mott1@gmail.com
- GitHub Issues: [Repository URL]

---

Last updated: January 2025
