# WoW Guild Analytics MCP Server

![MCPServer](https://badge.mcpx.dev?type=server)&nbsp;
![FastMCP](https://img.shields.io/badge/-FastMCP-05122A?style=flat)&nbsp;
![Python](https://img.shields.io/badge/-Python-05122A?style=flat&logo=python)&nbsp;
![FastAPI](https://img.shields.io/badge/-FastAPI-05122A?style=flat&logo=fastapi)&nbsp;
![Battle.net](https://img.shields.io/badge/-Battle.net-05122A?style=flat&logo=battle.net&logoColor=148EFF)&nbsp;
![Redis](https://img.shields.io/badge/-Redis-05122A?style=flat&logo=redis&logoColor=DD0031)&nbsp;
![Heroku](https://img.shields.io/badge/-Heroku-05122A?style=flat&logo=heroku&logoColor=430098)&nbsp;
![Supabase](https://img.shields.io/badge/-Supabase-05122A?style=flat&logo=supabase&logoColor=3ECF8E)&nbsp;
<a href="https://discord.com/users/479379710766481436"><img alt="Discord" src="https://img.shields.io/badge/Discord-%235865F2.svg?&style=flat&logo=discord&logoColor=white" /></a>&nbsp;
<a href="https://linkedin.com/in/noahmott"><img alt="LinkedIn" src="https://img.shields.io/badge/linkedin%20-%230077B5.svg?&style=flat&logo=linkedin&logoColor=white"/></a>&nbsp;

A Model Context Protocol (MCP) server providing comprehensive World of Warcraft guild analytics, auction house data, and market insights through the Blizzard Battle.net API. Built with FastMCP 2.0 and deployed on Heroku.

## Overview

This MCP server integrates with Claude Desktop (or any MCP client) to provide real-time WoW guild management, player analysis, and auction house economics data. It supports both Retail and Classic WoW with proper namespace handling, Redis caching for performance, and optional Supabase logging for user activity tracking.

## Features

- **Guild Management**: Retrieve guild rosters, member details, and raid progression data
- **Character Analysis**: Deep character inspection including equipment, specializations, achievements, and statistics
- **Auction House Economics**: Real-time commodity and auction house data with trend analysis
- **Market Intelligence**: Identify profitable trading opportunities and track price trends
- **Demographics Analytics**: Comprehensive guild demographic breakdowns by class, race, spec, and item level
- **Realm Information**: Server status and connected realm ID lookup
- **Item Lookup**: Batch item data retrieval with detailed metadata
- **Visualization**: Raid progress tracking and member performance comparisons
- **Redis Caching**: Optimized response times with intelligent cache management
- **OAuth Authentication**: Discord OAuth integration for user tracking
- **Activity Logging**: Supabase integration for usage analytics and monitoring

## Tech Stack

**Core Framework:**
- Python 3.13
- FastAPI 0.116.1
- FastMCP 2.0+ (Model Context Protocol)
- Uvicorn/Gunicorn (ASGI server)

**Data & Caching:**
- Redis 6.2 (caching and performance optimization)
- Supabase (activity logging and user tracking)
- SQLAlchemy 2.0 (database operations)

## Installation

### Prerequisites

- Python 3.13+
- Redis server (local or Heroku Redis)
- Blizzard Battle.net API credentials ([Get them here](https://develop.battle.net/))
- Supabase account (optional, for activity logging)

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

# Redis Configuration (REQUIRED)
REDIS_URL=redis://localhost:6379      # Local development
# Heroku automatically sets REDIS_URL for rediss://... (TLS)
```

### Optional

```bash
# OAuth Authentication (Optional)
OAUTH_PROVIDER=                       # Options: discord (empty = disabled)
OAUTH_BASE_URL=http://localhost:8000  # Your server's public URL
DISCORD_CLIENT_ID=                    # Discord OAuth credentials
DISCORD_CLIENT_SECRET=

# Supabase (Optional - Activity Logging)
SUPABASE_URL=                         # Your Supabase project URL
SUPABASE_SERVICE_KEY=                 # Service role key (bypasses RLS)

# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=false

# Feature Flags
ENABLE_REDIS_CACHING=true
ENABLE_SUPABASE_LOGGING=true
ENABLE_AI_ANALYSIS=true

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

2. Add Redis addon:
```bash
heroku addons:create heroku-redis:mini
```

3. Set environment variables:
```bash
heroku config:set BLIZZARD_CLIENT_ID=your_client_id
heroku config:set BLIZZARD_CLIENT_SECRET=your_client_secret
heroku config:set BLIZZARD_REGION=us
heroku config:set WOW_VERSION=retail
```

4. Deploy:
```bash
git push heroku main
```

5. Verify deployment:
```bash
heroku logs --tail
```

The server will automatically use the `REDIS_URL` environment variable set by the Heroku Redis addon.

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
Current market prices for commodities or auction house items.
- **Parameters**: `market_type`, `realm`, `item_ids`, `include_trends`, `trend_hours`, `max_results`, `game_version`
- **Market Types**: `commodities` (region-wide), `auction_house` (realm-specific)
- **Use Case**: Real-time market snapshots with optional historical trends

### 6. `analyze_market`
Find profitable trading opportunities or check economy snapshot health.
- **Parameters**: `operation`, `market_type`, `realm`, `min_profit_margin`, `check_hours`, `realms`, `max_results`, `game_version`
- **Operations**: `opportunities` (find deals), `health_check` (system status)
- **Use Case**: Identify underpriced items or monitor data collection health

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

## Caching Strategy

The server implements intelligent Redis caching:
- **Guild Rosters**: 15-day cache with age tracking
- **Economy Snapshots**: 30-day retention with hourly captures
- **Market Trends**: Rolling 30-day historical data
- **Cache Keys**: Namespaced by game version, region, and realm

## Monitoring & Logging

**Activity Logging** (via Supabase):
- All MCP tool calls logged with user tracking
- OAuth user attribution (Discord)
- Request/response metadata and duration tracking
- Error tracking and debugging

**Health Checks**:
- Redis connectivity status
- Blizzard API rate limits
- Supabase streaming status
- Economy snapshot freshness

## Rate Limits

**Blizzard API**:
- 100 requests per second (soft limit)
- 36,000 requests per hour (hard limit)
- Automatic retry with exponential backoff via tenacity

**Redis**:
- 50 max connections
- TLS support for Heroku Redis

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
