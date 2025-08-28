# Lobe Chat Integration Setup Guide

## Overview

This document provides comprehensive instructions for setting up and using the Lobe Chat interface with the AI Assistant backend. The integration provides a modern, user-friendly chat interface for interacting with our ReAct-powered trading AI assistant.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   Lobe Chat     │    │  Lobe Chat       │    │  AI Assistant   │    │  ReAct Agent     │
│   Frontend      │───▶│  Adapter         │───▶│  Backend        │───▶│  + Tools         │
│   (Port 3210)   │    │  (Port 8003)     │    │  (Port 8002)    │    │  + Memory        │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └──────────────────┘
```

### Components

1. **Lobe Chat Frontend** (Port 3210)
   - Modern React-based chat interface
   - Supports streaming responses
   - Customizable UI and branding
   - Session management

2. **Lobe Chat Adapter** (Port 8003)
   - OpenAI-compatible API bridge
   - Converts between Lobe Chat format and our AI Assistant API
   - Handles streaming responses
   - Formats reasoning traces for display

3. **AI Assistant Backend** (Port 8002)
   - ReAct agent with LangChain
   - Trading-specific tools and capabilities
   - Session-based conversation memory
   - Integration with Phase 2 API

4. **ReAct Agent + Tools**
   - Reasoning and Acting framework
   - Backtesting capabilities
   - Document querying
   - System status monitoring
   - Code development tools

## Prerequisites

- Docker and Docker Compose installed
- Environment variables configured (see `.env.example`)
- AI Assistant backend properly configured
- Valid API keys for LLM providers (OpenAI or Ollama)

## Installation and Setup

### 1. Environment Configuration

Create or update your `.env` file with the following variables:

```bash
# AI Assistant Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=openai  # or "ollama"
OPENAI_MODEL=gpt-3.5-turbo
TEMPERATURE=0.7
MAX_TOKENS=2000

# LOBE Chat Configuration
LOBE_ADAPTER_PORT=8003
LOBE_ALLOWED_ORIGINS=http://localhost:3210,http://localhost:3000
AI_ASSISTANT_URL=http://ai_assistant:8002

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:3210

# Optional: Ollama Configuration (if using local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### 2. Start the Services

Use Docker Compose to start all services:

```bash
# Start all services including Lobe Chat
docker-compose up -d

# Or start specific services
docker-compose up -d ai_assistant lobe_chat_adapter lobe_chat

# View logs
docker-compose logs -f lobe_chat
docker-compose logs -f lobe_chat_adapter
docker-compose logs -f ai_assistant
```

### 3. Verify Installation

Check that all services are running:

```bash
# Check service status
docker-compose ps

# Test health endpoints
curl http://localhost:8002/health  # AI Assistant
curl http://localhost:8003/health  # Lobe Chat Adapter
curl http://localhost:3210         # Lobe Chat Frontend
```

## Usage Guide

### Accessing Lobe Chat

1. Open your web browser and navigate to: `http://localhost:3210`
2. You should see the Lobe Chat interface with "Trading AI Assistant" branding
3. The interface will automatically connect to the AI Assistant backend

### Chat Features

#### Basic Chat
- Type your message in the input field
- Press Enter or click Send
- The AI will respond with reasoning traces visible

#### Advanced Features

1. **Reasoning Traces**
   - The assistant shows its thought process
   - Tool usage is displayed
   - Step-by-step reasoning is visible

2. **Trading-Specific Capabilities**
   - Run backtests: "Run a backtest for AAPL with moving average strategy"
   - Query documents: "What are the best practices for risk management?"
   - Check system status: "What's the current system status?"
   - Code development: "Create a new trading indicator"

3. **Session Management**
   - Conversations are maintained across messages
   - Each browser session gets a unique ID
   - Memory window of last 10 exchanges

### Example Conversations

#### Backtesting Query
```
User: "Run a backtest for Apple stock using a simple moving average crossover strategy"
Assistant: I'll analyze your request and run a backtest using the available tools.

🧠 **Reasoning Process**:

**Step 1 - Thought**: I need to run a backtest for Apple (AAPL) using a moving average crossover strategy. Let me use the backtesting tool.

**Action**: run_backtest_tool
**Input**: {"symbol": "AAPL", "strategy": "moving_average_crossover", "start_date": "2023-01-01", "end_date": "2023-12-31"}
**Result**: Backtest completed successfully. Strategy returned 15.2% with Sharpe ratio of 1.34...

🔧 **Tools Used**: run_backtest_tool

The backtest shows promising results for the moving average crossover strategy on Apple stock...
```

#### Document Query
```
User: "What are the key principles of risk management in algorithmic trading?"
Assistant: I'll search our trading documents for risk management principles.

🧠 **Reasoning Process**:

**Step 1 - Thought**: The user is asking about risk management principles. Let me query our document database for relevant information.

**Action**: query_documents_tool
**Input**: {"query": "risk management principles algorithmic trading", "max_results": 5}
**Result**: Found 3 relevant documents discussing position sizing, stop losses, diversification...

🔧 **Tools Used**: query_documents_tool

Based on our trading documentation, here are the key risk management principles:

1. **Position Sizing**: Never risk more than 2% of capital on a single trade
2. **Stop Losses**: Always define exit points before entering trades
3. **Diversification**: Spread risk across multiple assets and strategies
4. **Maximum Drawdown**: Set limits on portfolio-level losses
5. **Correlation Analysis**: Monitor asset correlations to avoid concentration risk
```

## Configuration

### Custom Model Configuration

The system comes pre-configured with a "trading-assistant" model. You can customize this in the docker-compose.yml:

```yaml
environment:
  CUSTOM_MODELS: '{"trading-assistant":{"displayName":"Trading Assistant","description":"Specialized AI assistant for algorithmic trading with reasoning capabilities","maxTokens":4000,"temperature":0.7}}'
```

### UI Customization

Customize the interface appearance:

```yaml
environment:
  APP_NAME: "Your Trading Assistant"
  APP_DESCRIPTION: "Custom description"
  PRIMARY_COLOR: "#1890ff"
```

### API Configuration

The adapter connects to the AI Assistant backend. Modify these settings if needed:

```yaml
environment:
  AI_ASSISTANT_URL: "http://ai_assistant:8002"
  OPENAI_PROXY_URL: "http://localhost:8003/v1"
```

## Troubleshooting

### Common Issues

#### 1. Lobe Chat Not Loading
```bash
# Check if the service is running
docker-compose ps lobe_chat

# Check logs
docker-compose logs lobe_chat

# Restart the service
docker-compose restart lobe_chat
```

#### 2. API Connection Issues
```bash
# Test the adapter endpoint
curl http://localhost:8003/health

# Test the AI Assistant endpoint
curl http://localhost:8002/health

# Check network connectivity
docker-compose exec lobe_chat_adapter ping ai_assistant
```

#### 3. Chat Not Responding
```bash
# Check adapter logs
docker-compose logs lobe_chat_adapter

# Test direct API call
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"trading-assistant","messages":[{"role":"user","content":"Hello"}]}'
```

#### 4. Reasoning Traces Not Showing
- Ensure the adapter is properly formatting responses
- Check that the AI Assistant is returning reasoning data
- Verify the frontend is configured to display reasoning

### Performance Optimization

#### 1. Response Time
- Use streaming responses for better perceived performance
- Optimize LLM model selection (faster models for simple queries)
- Implement response caching for common queries

#### 2. Memory Usage
- Monitor Docker container memory usage
- Adjust conversation memory window size
- Clear old sessions periodically

#### 3. Concurrent Users
- Scale adapter service horizontally if needed
- Implement rate limiting
- Monitor resource usage

### Security Considerations

#### 1. Access Control
```yaml
environment:
  ACCESS_CODE: "your-secure-access-code"
  ENABLE_OAUTH_SSO: "true"  # For production
```

#### 2. API Security
- Use HTTPS in production
- Implement proper authentication
- Validate all inputs

#### 3. Network Security
- Use Docker networks for service isolation
- Implement firewall rules
- Monitor access logs

## Development and Customization

### Adding Custom Features

#### 1. Custom Tools
Add new tools to the AI Assistant by modifying `tools.py`:

```python
def custom_trading_tool(input_data: str) -> str:
    """Custom tool for specific trading operations"""
    # Implementation here
    return result
```

#### 2. Custom UI Components
Extend Lobe Chat with custom components:

```javascript
// Custom trading dashboard component
const TradingDashboard = () => {
  // Component implementation
};
```

#### 3. Custom API Endpoints
Add new endpoints to the adapter:

```python
@app.post("/v1/custom/endpoint")
async def custom_endpoint(request: CustomRequest):
    # Custom logic here
    return response
```

### Testing

#### 1. Unit Tests
```bash
# Run adapter tests
cd ai_assistant
python -m pytest test_lobe_chat_adapter.py

# Run AI Assistant tests
python -m pytest test_react_agent.py
```

#### 2. Integration Tests
```bash
# Test full integration
curl -X POST http://localhost:8003/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"trading-assistant","messages":[{"role":"user","content":"Run a simple backtest"}],"stream":true}'
```

#### 3. Load Testing
```bash
# Use tools like Apache Bench or wrk
ab -n 100 -c 10 http://localhost:3210/
```

## Monitoring and Maintenance

### Health Checks
- Monitor all service health endpoints
- Set up alerts for service failures
- Implement automated recovery procedures

### Logging
- Centralize logs using ELK stack or similar
- Monitor error rates and response times
- Track user interactions and tool usage

### Updates
- Regularly update Lobe Chat image
- Update AI Assistant dependencies
- Monitor for security updates

## Support and Resources

### Documentation
- [Lobe Chat Official Documentation](https://lobehub.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Community
- GitHub Issues for bug reports
- Discord/Slack for community support
- Regular updates and feature announcements

### Professional Support
- Enterprise support options available
- Custom development services
- Training and consultation

---

## Quick Start Checklist

- [ ] Environment variables configured
- [ ] Docker services started
- [ ] Health checks passing
- [ ] Lobe Chat accessible at http://localhost:3210
- [ ] Test conversation completed
- [ ] Reasoning traces visible
- [ ] Tools working correctly

For additional help, check the logs or contact support.