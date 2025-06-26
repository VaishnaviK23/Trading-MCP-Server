# Trading-MCP-Server
An intelligent trading assistant that integrates with the Claude AI MCP (Model Context Protocol) platform. This tool fetches live stock prices using Yahoo Finance and enables seamless command-based interaction with the market via Claude's agent interface.

## 🚀 Features

- 🔄 Fetches real-time (or near real-time) stock prices using Yahoo Finance
- 🤖 Connects to Claude MCP as a server with custom trading commands
- 🛠 Built using Python with support for virtual environments and `uv` for dependency management
- ⚙️ Supports modular expansion to include trading signals, historical analysis, and more

## 🧠 Architecture

- **Claude AI MCP Integration**: Uses `mcp[cli]` to expose a server interface to Claude.
- **Yahoo Finance API**: For retrieving stock data (via `yfinance`).
- **Virtual Environment**: Managed using `uv` for fast and deterministic builds.

## 📦 Setup

```bash
# Install uv if not already installed
brew install uv

# Navigate to the project directory
cd MCPtrading

# Install dependencies
uv pip install -r requirements.txt

# (Optional) Add packages
uv add yfinance
```
## 🏃‍♀️ Running the Server

Make sure to use the correct Python environment:

```bash
uv run --python .venv/bin/python --with "mcp[cli]" mcp run trader_tools.py
```
Or update your Claude config:

```json
{
  "mcpServers": {
    "Trading": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": [
        "run",
        "--python",
        "/full/path/to/.venv/bin/python",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "trader_tools.py"
      ]
    }
  }
}
```
🧪 Example Usage

Ask Claude:

"What's the latest price of AAPL?"

Claude will call the MCP server and respond with the current stock price.

