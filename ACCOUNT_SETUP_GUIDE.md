# 🔧 Account Setup Guide for Algorithmic Trading System

## Overview
This guide provides step-by-step instructions for setting up all external accounts and services required for the Algorithmic Trading System to operate smoothly.

---

## 📧 Email Notification Setup (ALREADY CONFIGURED)

### ✅ Current Configuration
- **Provider**: Gmail SMTP
- **Status**: ✅ Already configured
- **Email**: vincyspereira@gmail.com
- **App Password**: ✅ Already set

### Gmail SMTP Settings (Reference)
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=vincyspereira@gmail.com
EMAIL_HOST_PASSWORD=vkid nfqn phcr rvpp  # App-specific password
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
```

**📝 Note**: Your Gmail is already configured with an app-specific password. Email notifications will work immediately.

---

## 🔔 Microsoft Teams Notifications (OPTIONAL)

### Setup Process:
1. **Open Microsoft Teams**
   - Go to the channel where you want notifications
   - Click the three dots (⋯) next to the channel name
   - Select \"Connectors\"

2. **Configure Incoming Webhook**
   - Search for \"Incoming Webhook\"
   - Click \"Configure\"
   - Give it a name: \"Algorithmic Trading Alerts\"
   - Optionally upload an icon
   - Click \"Create\"

3. **Copy Webhook URL**
   - Copy the webhook URL provided
   - Add to .env file:
   ```bash
   TEAMS_WEBHOOK_URL=https://your-tenant.webhook.office.com/webhookb2/...
   ```

### Required Information:
- ✅ Microsoft Teams account (Office 365)
- ✅ Team/Channel access permissions
- 📋 **Action**: Copy webhook URL to .env file

---

## 💬 Discord Notifications (OPTIONAL)

### Setup Process:
1. **Open Discord Server**
   - Go to your Discord server
   - Right-click on the channel for notifications
   - Select \"Edit Channel\"

2. **Create Webhook**
   - Go to \"Integrations\" tab
   - Click \"Create Webhook\"
   - Name: \"Trading System Alerts\"
   - Select the channel
   - Copy webhook URL

3. **Add to Configuration**
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

### Required Information:
- ✅ Discord account
- ✅ Server administration permissions
- 📋 **Action**: Copy webhook URL to .env file

---

## 💾 Redis Configuration (REQUIRED)

### Option 1: Local Redis (Recommended for Development)
```bash
# Already configured in .env
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=  # Empty for local development
```

### Option 2: Redis Cloud (Production)
1. **Create Account**
   - Go to https://redis.com/try-free/
   - Sign up for free account
   - Create a new database

2. **Get Connection Details**
   - Copy endpoint, port, and password
   - Update .env:
   ```bash
   REDIS_HOST=redis-xxxxx.cloud.redislabs.com
   REDIS_PORT=12345
   REDIS_PASSWORD=your_redis_password
   ```

### Required Information:
- 📋 **Action**: Use Docker Redis (no additional setup needed)
- 🔄 **Alternative**: Redis Cloud account for production

---

## 📊 Database Services

### PostgreSQL (ALREADY CONFIGURED)
```bash
# Already set up in .env
POSTGRES_HOST=postgres
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD="password"
POSTGRES_DB=trading_system_prod
```
✅ **Status**: Ready to use with Docker

### ClickHouse (ANALYTICS DATABASE)
```bash
# Already configured for Docker
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=trading_analytics
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
```
✅ **Status**: Ready to use with Docker

---

## 📈 Market Data & Broker Integration

### 🏦 Interactive Brokers (PRIMARY BROKER)
**Status**: ✅ Ready for Paper Trading
**Configuration**: Already set for paper trading mode

```bash
# Primary broker configuration (already set)
IB_GATEWAY_HOST=localhost
IB_GATEWAY_PORT=7497
IB_CLIENT_ID=1
IB_PAPER_TRADING=true  # Paper trading mode
ENABLE_LIVE_TRADING=false  # Safety flag
ENABLE_PAPER_TRADING=true  # Paper trading enabled
```

#### Paper Trading Setup (FREE):
1. **Create IBKR Paper Trading Account**
   - Go to https://www.interactivebrokers.com/
   - Open a paper trading account (completely free)
   - No minimum deposit required for paper trading

2. **Install IB Gateway/TWS**
   - Download IB Gateway (lighter) or TWS (full platform)
   - Configure for paper trading mode
   - Enable API connections
   - Set socket port to 7497 (paper trading port)

#### Live Trading Setup (FUTURE):
- When ready for live trading, change `IB_PAPER_TRADING=false`
- Switch to port 7496 for live trading
- Subscribe to IBKR market data packages
- **Note**: Live trading requires funded account

### 📊 Market Data Sources (Multi-Source with Fallback)

#### Primary Data Source: Yahoo Finance (FREE)
```bash
YAHOO_FINANCE_ENABLED=true  # Already enabled
```
✅ **Status**: Free, no API key required
✅ **Coverage**: Stocks, ETFs, indices, forex, crypto
✅ **Limitations**: 15-minute delay for some data

#### Secondary Data Sources (Additional Brokers)

##### Alpha Vantage (ADDITIONAL BROKER - NOT PRIMARY)
**Purpose**: Additional broker integration + backup data source
**Current Status**: Placeholder key needs replacement

```bash
# Replace this dummy key when integrating Alpha Vantage as additional broker
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

**Setup Process**:
1. **Create Account**: https://www.alphavantage.co/support/#api-key
2. **Free Tier**: 5 API requests per minute, 500 per day
3. **Usage**: Secondary broker + data fallback (not primary broker)

##### Finnhub (BACKUP DATA SOURCE)
**Purpose**: Fallback data source for market data
**Status**: Optional for paper trading, recommended for production

```bash
FINNHUB_API_KEY=your_finnhub_api_key  # Optional for paper trading
```

**Setup Process**:
1. **Create Account**: https://finnhub.io/register
2. **Free Tier**: 60 API calls/minute
3. **Usage**: Backup data source in fallback mechanism

##### Twelve Data (ALTERNATIVE BACKUP)
**Purpose**: Additional fallback data source
**Status**: Optional for paper trading

```bash
TWELVE_DATA_API_KEY=your_twelve_data_api_key  # Optional
```

### 🔄 Multi-Source Data Feed Fallback Mechanism

The system implements automatic fallback:
```
1. Primary: IBKR Market Data (Paper Trading: Free, Live: Paid)
2. Fallback 1: Yahoo Finance (Free)
3. Fallback 2: Alpha Vantage (Free tier: 500 calls/day)
4. Fallback 3: Finnhub (Free tier: 60 calls/minute)
5. Fallback 4: Twelve Data (Free tier: 800 calls/day)
```

**Paper Trading Recommendation**: Use only Yahoo Finance + IBKR paper data (both free)
**Live Trading**: Subscribe to IBKR market data + keep free fallbacks

### 🌍 Additional Broker Integration (FUTURE)

#### Oanda (Forex Specialist)
```bash
# Future integration
OANDA_API_KEY=
OANDA_ACCOUNT_ID=
OANDA_ENVIRONMENT=practice  # For testing
```

#### Coinbase (Crypto Specialist)
```bash
# Future integration
COINBASE_API_KEY=
COINBASE_API_SECRET=
COINBASE_PASSPHRASE=
COINBASE_SANDBOX=true  # For testing
```

**Note**: These additional brokers will be integrated as secondary brokers alongside IBKR primary broker.

---

## 🤖 AI/ML Services

### OpenAI API (AI ASSISTANT)
1. **Create Account**
   - Go to https://platform.openai.com/signup
   - Add payment method (required for API access)
   - Create API key

2. **Configuration**
   ```bash
   OPENAI_API_KEY=sk-your_openai_api_key_here
   ```

### HuggingFace (MODEL ACCESS)
1. **Create Account**
   - Go to https://huggingface.co/join
   - Create free account
   - Go to Settings → Access Tokens
   - Create new token

2. **Configuration**
   ```bash
   HUGGINGFACE_TOKEN=hf_your_huggingface_token
   ```

### Required Information:
- 💳 **OpenAI**: Credit card required for API access
- ✅ **HuggingFace**: Free account sufficient
- 📋 **Action**: Get API keys and add to .env

---

## 🔒 Security & Vulnerability Scanning

### GitHub Token (ALREADY CONFIGURED)
```bash
# Already set in .env
GITHUB_TOKEN=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
```
✅ **Status**: Ready to use

### NVD API (CVE DATABASE)
1. **Request API Key** (Optional but Recommended)
   - Go to https://nvd.nist.gov/developers/request-an-api-key
   - Fill out the form
   - Wait for approval (usually 1-2 days)

2. **Configuration**
   ```bash
   NVD_API_KEY=your_nvd_api_key  # Optional, higher rate limits
   ```

### Required Information:
- ✅ **GitHub**: Already configured
- 📋 **NVD**: Optional API key for higher rate limits

---

## 🏦 Trading Broker Integration

### Interactive Brokers (PRIMARY BROKER)
**Status**: ✅ Configured for Paper Trading
**Purpose**: Primary broker for both paper and live trading

```bash
# Primary broker configuration (already configured)
IB_GATEWAY_HOST=localhost
IB_GATEWAY_PORT=7497  # Paper trading port
IB_CLIENT_ID=1
IB_PAPER_TRADING=true  # Paper trading mode
ENABLE_LIVE_TRADING=false  # Safety flag
ENABLE_PAPER_TRADING=true  # Paper trading enabled
```

### Paper Trading Setup (FREE):
1. **Create IBKR Paper Trading Account**
   - Go to https://www.interactivebrokers.com/
   - Open a paper trading account (completely free)
   - No minimum deposit or fees for paper trading
   - Access to same trading platform as live accounts

2. **Install and Configure IB Gateway**
   - Download IB Gateway (recommended) or TWS
   - Configure for paper trading mode
   - Enable API connections in settings
   - Set socket port to 7497 (paper trading port)
   - Create API client configuration

3. **Paper Trading Benefits**
   - ✅ Free market data for US stocks
   - ✅ Real-time quotes during market hours
   - ✅ Full order types and trading features
   - ✅ Portfolio tracking and reporting
   - ✅ Risk management tools

### Live Trading Setup (FUTURE PHASE):
1. **When Ready for Live Trading**
   - Change `IB_PAPER_TRADING=false`
   - Change `IB_GATEWAY_PORT=7496` (live trading port)
   - Set `ENABLE_LIVE_TRADING=true`
   - Fund your IBKR account

2. **Market Data Subscriptions** (Live Trading Only)
   - Subscribe to IBKR market data packages
   - Real-time quotes for global markets
   - Level II data for advanced trading
   - **Cost**: Varies by package ($1-50/month typically)

### Required Information for Paper Trading:
- ✅ **IBKR Paper Trading Account**: Free registration
- ✅ **IB Gateway/TWS**: Free download and installation
- ✅ **API Configuration**: Enable API access in platform
- 📋 **Action**: Create paper trading account and install software

---

## 🔍 Vector Database (AI FEATURES)

### Qdrant (VECTOR SEARCH)
```bash
# Already configured for local development
QDRANT_API_KEY=  # Empty for local Docker instance
```

### Cloud Option:
1. **Create Qdrant Cloud Account**
   - Go to https://cloud.qdrant.io/
   - Sign up for free account
   - Create cluster
   - Get API key and endpoint

2. **Configuration**
   ```bash
   QDRANT_API_KEY=your_qdrant_api_key
   QDRANT_URL=https://your-cluster.qdrant.io
   ```

---

## 📋 Priority Setup Checklist

### 🚨 Critical (System Won't Start Without These)
- ✅ **Email Configuration**: Already done
- ✅ **Database Passwords**: Already set
- ✅ **Redis**: Uses Docker (no setup needed)
- ✅ **IBKR Paper Trading**: Primary broker (free setup required)
- 🔄 **Market Data**: Yahoo Finance (free, no API key needed)

### ⚠️ High Priority (Core Functionality)
- 📋 **IBKR Paper Account**: Create and configure (free)
- 📋 **IB Gateway**: Install and configure (free)
- 🔄 **OpenAI API Key**: For AI assistant (optional for paper trading)

### 📝 Medium Priority (Enhanced Features - Optional for Paper Trading)
- 📋 **Alpha Vantage API**: Additional broker integration (free tier)
- 📋 **Finnhub API Key**: Backup data source (free tier)
- 📋 **Teams Webhook**: For team notifications
- 📋 **Discord Webhook**: For community alerts

### 🔧 Low Priority (Production Features)
- 📋 **Twelve Data API**: Alternative backup data source
- 📋 **NVD API Key**: Higher rate limits for security scanning
- 📋 **HuggingFace Token**: For advanced ML models
- 📋 **Qdrant Cloud**: Production vector database

---

## 🚀 Quick Start Commands

### 1. Update .env File
```bash
# Copy the template and edit
cp .env.example .env
# Edit .env with your API keys
```

### 2. Test Email Notifications
```bash
# Navigate to notification service
cd services/dependency_management_service/notification_service/

# Run email test
python test_email_notifications.py
```

### 3. Start the System
```bash
# Start core services
docker-compose --profile core up -d

# Start with monitoring
docker-compose --profile core --profile monitoring up -d

# Full system with AI
docker-compose --profile pro up -d
```

---

## 💡 Cost Breakdown

### Paper Trading Phase (FREE TIER FOCUS)
- ✅ **IBKR Paper Trading**: Free (includes basic market data)
- ✅ **Yahoo Finance Data**: Free
- ✅ **Gmail SMTP**: Free
- ✅ **Teams/Discord**: Free with existing accounts
- ✅ **Redis (Local)**: Free with Docker
- ✅ **All Database Services**: Free with Docker
- ✅ **Alpha Vantage**: Free tier (500 calls/day)
- ✅ **Finnhub**: Free tier (60 calls/minute) - Optional
- ✅ **Twelve Data**: Free tier (800 calls/day) - Optional

**Total Paper Trading Cost: $0/month** 🎉

### Live Trading Phase (PRODUCTION)
- 💳 **IBKR Market Data**: $1-50/month (depending on packages)
- 💳 **OpenAI API**: $10-50/month (for advanced AI features)
- 💳 **Redis Cloud**: $5/month (for production scaling)
- 💳 **Upgraded API Limits**: $20-100/month (optional)

**Total Live Trading Cost: ~$40-200/month**

### Recommended Approach:
1. **Phase 1**: Start with 100% free tier for paper trading
2. **Phase 2**: Test thoroughly with free services
3. **Phase 3**: Gradually upgrade to paid services for live trading
4. **Phase 4**: Scale based on trading volume and requirements

---

## 🆘 Support & Troubleshooting

### Common Issues
1. **Email Not Sending**
   - Check Gmail app password
   - Verify SMTP settings
   - Check firewall settings

2. **API Rate Limits**
   - Monitor API usage
   - Consider upgrading to paid tiers
   - Implement request caching

3. **Database Connection Issues**
   - Verify Docker containers are running
   - Check port configurations
   - Review password settings

### Testing Commands
```bash
# Test email notifications
python test_email_notifications.py

# Check Docker services
docker-compose ps

# View logs
docker-compose logs -f notification-service
```

---

## 📞 Next Steps for Paper Trading

### Immediate Setup (This Week)
1. **✅ Email System**: Already configured and working
2. **📋 IBKR Paper Account**: Create free paper trading account
3. **📋 IB Gateway**: Download and configure (free)
4. **🔄 Test Paper Trading**: Verify connection with system

### Optional Enhancements (Next Week)
1. **📋 Alpha Vantage API**: For additional broker integration
2. **📋 Teams/Discord**: For notification testing
3. **📋 Finnhub API**: For data redundancy testing

### Future Live Trading Preparation
1. **Fund IBKR Account**: When ready for live trading
2. **Subscribe to Market Data**: IBKR professional data feeds
3. **Upgrade API Limits**: For higher frequency trading
4. **Production Infrastructure**: Paid cloud services

**🎯 Primary Goal**: Complete paper trading setup with 100% free services within 3-5 days
**🚀 Secondary Goal**: Thoroughly test all features before considering live trading
**💰 Budget**: $0 for paper trading phase, plan budget for live trading phase