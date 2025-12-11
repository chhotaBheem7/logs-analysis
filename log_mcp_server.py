from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
from log_agent import fetch_logs, analyze_logs_with_gemini # Import your functions

load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("LogAnalyzer")

@mcp.tool()
def check_server_health(lines: int = 200) -> str:
    """
    Fetches server logs via SSH and uses Gemini to analyze them for errors.
    Returns a health report.
    """
    # 1. Configuration (Load from env or hardcode for now)
    SERVER_IP = os.getenv("SSH_HOST")
    SSH_USER = os.getenv("SSH_USER")
    SSH_KEY = os.getenv("SSH_KEY_PATH")
    LOG_PATH = "/var/log/syslog" 

    # 2. Reuse your existing logic
    raw_logs = fetch_logs(SERVER_IP, SSH_USER, SSH_KEY, LOG_PATH, lines)
    
    if "CRITICAL_AGENT_ERROR" in raw_logs:
        return raw_logs

    # 3. Analyze
    analysis = analyze_logs_with_gemini(raw_logs)
    return analysis

if __name__ == "__main__":
    mcp.run()
