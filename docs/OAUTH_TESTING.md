# OAuth Testing Guide

## Server Status
OAuth is successfully deployed and running on Heroku!

Base URL: `https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com`

## OAuth Endpoints

### 1. Discovery Endpoint (OAuth Metadata)
```bash
curl https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/.well-known/oauth-authorization-server
```

Response includes:
- `authorization_endpoint`: `/authorize`
- `token_endpoint`: `/token`
- `registration_endpoint`: `/register`
- `scopes_supported`: `["identify", "email"]`
- PKCE support with `S256` code challenge method

### 2. Authorization Endpoint
`GET /authorize`

Required parameters:
- `client_id`: Your registered client ID
- `redirect_uri`: Callback URL for your application
- `response_type`: Must be `code`
- `scope`: Space-separated scopes (e.g., `identify email`)
- `code_challenge`: PKCE challenge (S256 method)
- `code_challenge_method`: Must be `S256`

Example:
```bash
# This will redirect to Discord OAuth login
https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_CALLBACK&response_type=code&scope=identify+email&code_challenge=CHALLENGE&code_challenge_method=S256
```

### 3. Token Endpoint
`POST /token`

Exchange authorization code for access token:
```bash
curl -X POST https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "redirect_uri=YOUR_CALLBACK" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code_verifier=VERIFIER"
```

### 4. Client Registration Endpoint
`POST /register`

Register a new OAuth client dynamically.

## Current Configuration

### Provider
- **Discord OAuth**
- Client ID: `1435709923655942144`
- Scopes: `identify`, `email`

### Discord Configuration
Make sure your Discord application has the following redirect URI configured:
```
https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/callback
```

Configure at: https://discord.com/developers/applications/1435709923655942144/oauth2/general

## Testing with Claude Desktop

To test the OAuth flow with Claude Desktop, you need to configure the MCP server in your Claude Desktop config:

### Mac/Linux
`~/Library/Application Support/Claude/config.json`

### Windows
`%APPDATA%\Claude\config.json`

Add this configuration:
```json
{
  "mcpServers": {
    "wow-guild-mcp": {
      "url": "https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/mcp",
      "auth": {
        "type": "oauth2",
        "authorizationUrl": "https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/authorize",
        "tokenUrl": "https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/token",
        "scopes": ["identify", "email"]
      }
    }
  }
}
```

## Testing the Full Flow

1. **Start OAuth Flow**: Navigate to the authorization URL with proper PKCE parameters
2. **User Login**: User is redirected to Discord to authenticate
3. **Authorization**: User grants permission to your application
4. **Callback**: Discord redirects back with authorization code
5. **Token Exchange**: Exchange code for access token using the token endpoint
6. **MCP Access**: Use the access token to authenticate MCP requests

## User Tracking

When a user authenticates, the following data is tracked in Supabase:
- User profile (ID, email, username from Discord)
- Active sessions
- Activity logs (tool calls, queries, timestamps)

## Verification Steps

1. Check OAuth metadata:
```bash
curl https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/.well-known/oauth-authorization-server | jq
```

2. Verify server is running:
```bash
curl https://wow-guild-mcp-server-7f17b3f6ea0a.herokuapp.com/mcp
```

3. Check Heroku logs:
```bash
heroku logs --tail --app wow-guild-mcp-server
```

## Security Features

- OAuth 2.1 compliant
- PKCE (Proof Key for Code Exchange) required
- Token verification via Discord API
- Secure token storage and session management
- User activity logging for audit trails

## Next Steps

1. Register OAuth client (if using dynamic registration)
2. Implement PKCE in your client application
3. Test the full authorization flow
4. Verify user data appears in Supabase
5. Test MCP tool calls with authenticated users
