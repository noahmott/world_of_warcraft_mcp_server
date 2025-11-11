# WoW Guild Analytics MCP Server

![MCPServer](https://badge.mcpx.dev?type=server)&nbsp;
![FastMCP](https://img.shields.io/badge/-FastMCP-05122A?style=flat)&nbsp;
![Python](https://img.shields.io/badge/-Python-05122A?style=flat&logo=python)&nbsp;
![FastAPI](https://img.shields.io/badge/-FastAPI-05122A?style=flat&logo=fastapi)&nbsp;
![n8n](https://img.shields.io/badge/-n8n-05122A?style=flat&logo=n8n&logoColor=EA4B71)&nbsp;
![Battle.net](https://img.shields.io/badge/-Battle.net-05122A?style=flat&logo=battle.net&logoColor=148EFF)&nbsp;
![Heroku](https://img.shields.io/badge/-Heroku-05122A?style=flat&logo=heroku&logoColor=430098)&nbsp;
![Supabase](https://img.shields.io/badge/-Supabase-05122A?style=flat&logo=supabase&logoColor=3ECF8E)&nbsp;
<a href="https://discord.com/users/479379710766481436"><img alt="Discord" src="https://img.shields.io/badge/Discord-%235865F2.svg?&style=flat&logo=discord&logoColor=white" /></a>&nbsp;
<a href="https://linkedin.com/in/noahmott"><img alt="LinkedIn" src="https://img.shields.io/badge/linkedin%20-%230077B5.svg?&style=flat&logo=linkedin&logoColor=white"/></a>&nbsp;

A Model Context Protocol (MCP) server providing comprehensive World of Warcraft guild analytics and commodity market insights. Built with FastMCP 2.0 and deployed on Heroku with n8n data collection pipeline.

## Overview

This MCP server integrates with Claude Desktop (or any MCP client) to provide real-time WoW guild management, player analysis, and commodity market economics data.

**Data Pipeline Architecture:**
- **Commodity Market Data**: Automated n8n workflows pull from Blizzard API hourly → Store in Supabase → MCP queries database (10-100x faster than API)
- **Guild & Character Data**: Direct Blizzard API calls for real-time data
- **Activity Tracking**: All MCP tool usage logged to Supabase with Discord OAuth user attribution

## Features

- **Guild Management**: Retrieve guild rosters, member details, and raid progression data
- **Character Analysis**: Deep character inspection including equipment, specializations, achievements, and statistics
- **Commodity Market Economics**: Real-time commodity pricing data (ore, herbs, reagents) with historical trend analysis
- **Market Intelligence**: Identify profitable trading opportunities with price variance analysis
- **Demographics Analytics**: Comprehensive guild demographic breakdowns by class, race, spec, and item level
- **Realm Information**: Server status and connected realm ID lookup
- **Item Lookup**: Batch item data retrieval with detailed metadata
- **Visualization**: Raid progress tracking and member performance comparisons
- **OAuth Authentication**: Discord OAuth integration for user tracking
- **Activity Logging**: Supabase integration for usage analytics and monitoring

## Tech Stack

**Core Framework:**
- Python 3.13
- FastAPI 0.116.1
- FastMCP 2.0+ (Model Context Protocol)
- Uvicorn/Gunicorn (ASGI server)

**Data Storage:**
- Supabase (commodity market data storage and activity logging)
- n8n (automated commodity data collection from Blizzard API)

## Installation

### Prerequisites

- Python 3.13+
- Blizzard Battle.net API credentials ([Get them here](https://develop.battle.net/))
- Supabase account (for commodity market data and activity logging)

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/noahmott/mcp_wowconomics_server.git
cd mcp_wowconomics_server
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate 
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

5. Run the server:
```bash
python -m app.server
```

The server will start on `http://localhost:8000` with the MCP endpoint at `/mcp`.

### Claude Desktop Integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wow-guild-analytics": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

For production (Heroku):
```json
{
  "mcpServers": {
    "wow-guild-analytics": {
      "url": "https://your-app-name.herokuapp.com/mcp",
      "transport": "http"
    }
  }
}
```

## Environment Variables

### Required

```bash
# Blizzard API Credentials (REQUIRED)
BLIZZARD_CLIENT_ID=your_blizzard_client_id_here
BLIZZARD_CLIENT_SECRET=your_blizzard_client_secret_here

# Supabase Configuration (REQUIRED for commodity data)
SUPABASE_URL=                         # Your Supabase project URL
SUPABASE_SERVICE_KEY=                 # Service role key (bypasses RLS)
```

### Optional

```bash
# OAuth Authentication (Optional)
OAUTH_PROVIDER=                       # Options: discord (empty = disabled)
OAUTH_BASE_URL=http://localhost:8000  # Your server's public URL
DISCORD_CLIENT_ID=                    # Discord OAuth credentials
DISCORD_CLIENT_SECRET=

# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=false

# API Timeouts (seconds) Necessary for reducing API traffick to Blizzard
API_TIMEOUT_TOTAL=300
API_TIMEOUT_CONNECT=10
API_TIMEOUT_READ=60
```

## Deployment

### Heroku Deployment

1. Create a Heroku app:
```bash
heroku create your-app-name
```

2. Set environment variables:
```bash
heroku config:set BLIZZARD_CLIENT_ID=your_client_id
heroku config:set BLIZZARD_CLIENT_SECRET=your_client_secret
heroku config:set BLIZZARD_REGION=us
heroku config:set WOW_VERSION=retail
heroku config:set SUPABASE_URL=your_supabase_url
heroku config:set SUPABASE_SERVICE_KEY=your_service_key
```

3. Deploy:
```bash
git push heroku main
```

4. Verify deployment:
```bash
heroku logs --tail
```

### Docker Deployment (Alternative)

```bash
docker build -t wow-mcp-server .
docker run -p 8000:8000 --env-file .env wow-mcp-server
```

## MCP Tools Available

The server exposes 9 MCP tools for guild and economy analysis:

### 1. `get_guild_member_list`
Retrieve guild roster with sorting and filtering options.
- **Parameters**: `realm`, `guild_name`, `sort_by`, `limit`, `quick_mode`, `game_version`
- **Use Case**: Get overview of guild members, sorted by rank/level/name

### 2. `get_character_details`
Deep character inspection with equipment, specs, achievements, and statistics.
- **Parameters**: `realm`, `character_name`, `sections`, `game_version`
- **Sections**: profile, equipment, specializations, achievements, statistics, media, pvp, appearance, collections, titles, mythic_plus
- **Use Case**: Detailed player analysis for recruitment or progression planning

### 3. `get_realm_info`
Retrieve realm status and connected realm ID for auction house queries.
- **Parameters**: `realm`, `game_version`, `include_status`
- **Use Case**: Lookup realm IDs before querying realm-specific auction houses

### 4. `lookup_items`
Batch item lookup by ID with detailed metadata.
- **Parameters**: `item_ids` (int or list), `game_version`, `detailed`
- **Use Case**: Get item names, quality, prices, and stats for market analysis

### 5. `get_market_data`
Current commodity market prices (ore, herbs, reagents, etc.) from Supabase.
- **Parameters**: `item_ids`, `include_trends`, `trend_hours`, `max_results`, `region`
- **Data Source**: Supabase (collected via n8n from Blizzard API)
- **Use Case**: Real-time region-wide commodity market snapshots with optional historical trends

### 6. `analyze_market`
Find profitable commodity trading opportunities or check data collection health.
- **Parameters**: `operation`, `min_profit_margin`, `max_results`, `region`
- **Operations**: `opportunities` (find deals), `health_check` (check n8n data freshness)
- **Use Case**: Identify commodities with high price variance or monitor data pipeline health

### 7. `get_guild_raid_progression`
Guild achievement data including raid progression.
- **Parameters**: `realm`, `guild_name`, `game_version`
- **Use Case**: Track guild raid progression and achievement milestones

### 8. `compare_member_performance`
Compare performance metrics across guild members.
- **Parameters**: `realm`, `guild_name`, `member_names`, `metric`, `game_version`
- **Metrics**: `item_level`, `achievement_points`, `guild_rank`
- **Use Case**: Performance comparisons for raid team optimization

### 9. `get_guild_demographics`
Comprehensive demographic breakdown of guild composition.
- **Parameters**: `realm`, `guild_name`, `game_version`, `max_level_only`
- **Use Case**: Analyze guild composition by class, race, spec, faction, and item level

## API Documentation

### Base URL
- **Local**: `http://localhost:8000`
- **Production**: `https://your-app-name.herokuapp.com`

### MCP Endpoint
- **Path**: `/mcp`
- **Protocol**: HTTP transport (FastMCP 2.0)
- **Authentication**: Optional OAuth (Discord)

### Health Check
```bash
curl http://localhost:8000/health
```

### Example MCP Tool Call

Through Claude Desktop or any MCP client:
```
Get the member list for guild "Liquid" on Illidan realm
```

Claude will automatically call:
```json
{
  "tool": "get_guild_member_list",
  "arguments": {
    "realm": "illidan",
    "guild_name": "liquid",
    "sort_by": "guild_rank",
    "limit": 50,
    "game_version": "retail"
  }
}
```

## Development

### Project Structure
```
mcp_wowconomics_server/
├── app/
│   ├── server.py                  # Main MCP server
│   ├── api/
│   │   ├── blizzard_client.py     # Blizzard API client
│   │   └── guild_optimizations.py # Optimized guild fetching
│   ├── tools/
│   │   ├── guild_tools.py         # Guild roster tools
│   │   ├── member_tools.py        # Character analysis tools
│   │   ├── realm_tools.py         # Realm lookup tools
│   │   ├── item_tools.py          # Item data tools
│   │   ├── auction_tools.py       # Market analysis tools
│   │   ├── visualization_tools.py # Chart generation tools
│   │   └── demographics_tools.py  # Demographics analysis
│   ├── services/
│   │   ├── activity_logger.py     # Activity logging service
│   │   ├── auction_aggregator.py  # Auction data aggregation
│   │   ├── market_history.py      # Market history tracking
│   │   ├── supabase_client.py     # Supabase integration
│   │   └── supabase_streaming.py  # Real-time streaming
│   ├── core/
│   │   ├── auth.py                # OAuth authentication
│   │   ├── constants.py           # Game constants
│   │   └── discord_token_verifier.py
│   └── utils/
│       ├── datetime_utils.py      # Time utilities
│       ├── logging_utils.py       # Logging configuration
│       ├── namespace_utils.py     # WoW namespace handling
│       └── response_utils.py      # Response formatting
├── requirements.txt
├── Procfile                       # Heroku configuration
├── .env.example                   # Environment template
└── README.md
```

## Data Architecture

**Commodity Market Data** (via n8n + Supabase):
- **Collection**: n8n workflow pulls from Blizzard API hourly
- **Storage**: Supabase `commodity_auctions` table
- **Retention**: Configurable (90+ days supported based on storage)
- **Performance**: Direct database queries - much faster than API calls

**Guild & Character Data** (via Blizzard API):
- **Guild Rosters**: Real-time API calls for up-to-date member data
- **Character Data**: Real-time API calls with detailed profile information

## Monitoring & Logging

**Activity Logging** (via Supabase):
- All MCP tool calls logged with user tracking
- OAuth user attribution (Discord)
- Request/response metadata and duration tracking
- Error tracking and debugging

**Health Checks**:
- Blizzard API rate limits
- Supabase connectivity status
- Commodity data freshness (n8n workflow health)

## Rate Limits

**Blizzard API**:
- 100 requests per second (soft limit)
- 36,000 requests per hour (hard limit)
- Automatic retry with exponential backoff via tenacity

**Supabase**:
- Database queries for commodity data
- Activity logging with Discord OAuth attribution

## Contributing

Contributions are welcome. Please follow these guidelines:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests:
- **Discord**: [Contact me](https://discord.com/users/479379710766481436)
- **LinkedIn**: [Noah Mott](https://linkedin.com/in/noahmott)
- **GitHub Issues**: [Open an issue](https://github.com/noahmott/mcp_wowconomics_server/issues)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) by Marvin AI
- Powered by [Blizzard Battle.net API](https://develop.battle.net/)
- Deployed on [Heroku](https://heroku.com)
- Activity tracking via [Supabase](https://supabase.com)

## Roadmap

- [ ] Add additional authentication routes
- [ ] PvP arena statistics and rankings
- [ ] Discord bot integration
- [ ] Long-term collection and analysis of WoW commodities market for research
