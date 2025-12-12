from mcp.server.fastmcp import FastMCP
import os
import json
from dotenv import load_dotenv
from deployment_agent import DeploymentManager
from db_utils import DatabaseHandler

load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("JavaDeployer")

# Helper to get manager
def get_manager(hostname=None):
    host = hostname or os.getenv("SSH_HOST")
    user = os.getenv("SSH_USER")
    key = os.getenv("SSH_KEY_PATH")
    if not host or not user or not key:
        return None, "Missing SSH configuration (SSH_HOST, SSH_USER, SSH_KEY_PATH)"
    
    return DeploymentManager(host, user, key), None

@mcp.tool()
def deploy_java_app(local_jar_path: str, app_name: str, target_host: str = None) -> str:
    """
    Deploys a Java JAR file to the target server.
    Installs Java if missing, sets up systemd, and restarts the service.
    """
    manager, error = get_manager(target_host)
    if error: return error

    try:
        manager.connect()
        # 1. Ensure Java
        if not manager.install_java():
            return "Failed to install Java."
        
        # 2. Deploy
        if manager.deploy_jar(local_jar_path, app_name):
            return f"Successfully deployed {app_name} to {manager.hostname}"
        else:
            return "Deployment failed during JAR transfer or Service restart."
    except Exception as e:
        return f"Deployment Error: {str(e)}"
    finally:
        manager.close()

@mcp.tool()
def seed_database(table_name: str, data_json: str, db_url_override: str = None) -> str:
    """
    Inserts data into the database.
    data_json should be a JSON string representing a list of objects.
    Example: '[{"name": "Alice", "role": "Admin"}]'
    """
    return f"Database Error: {str(e)}"

def get_db_url(override=None):
    """
    Resolves the database URL from override, DB_URL env, or individual env vars.
    """
    if override: return override
    
    # 1. Try full URL
    url = os.getenv("DB_URL")
    if url: return url

    # 2. Try granular variables
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")

    if user and password and dbname:
        # Defaulting to PostgreSQL driver for now, can be made configurable
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    return None

@mcp.tool()
def seed_database(table_name: str, data_json: str, db_url_override: str = None) -> str:
    """
    Inserts data into the database.
    data_json should be a JSON string representing a list of objects.
    Example: '[{"name": "Alice", "role": "Admin"}]'
    """
    url = get_db_url(db_url_override)
    if not url:
        return "Missing Database configuration. Set DB_URL or (DB_USER, DB_PASSWORD, DB_NAME)."
    
    try:
        data = json.loads(data_json)
        if not isinstance(data, list):
            return "data_json must be a list of objects."
            
        db = DatabaseHandler(url)
        if db.seed_data(table_name, data):
            return f"Successfully inserted {len(data)} rows into {table_name}."
        else:
            return "Failed to seed data."
    except json.JSONDecodeError:
        return "Invalid JSON format."
    except Exception as e:
        return f"Database Error: {str(e)}"

@mcp.tool()
def check_app_health(app_port: int, target_host: str = None) -> str:
    """
    Checks if a service is responding on the given port.
    """
    manager, error = get_manager(target_host)
    if error: return error
    
    try:
        manager.connect()
        # Simple curl check
        success, out = manager.run_command(f"curl -s -o /dev/null -w '%{{http_code}}' localhost:{app_port}")
        
        if success and out == "200":
            return "Healthy (HTTP 200)"
        else:
            return f"Unhealthy. HTTP Status: {out}"
    except Exception as e:
        return f"Health Check Error: {e}"
    finally:
        manager.close()

@mcp.tool()
def get_server_stats(target_host: str = None) -> str:
    """
    Retrieves current server statistics (CPU, RAM, Disk).
    """
    manager, error = get_manager(target_host)
    if error: return error

    try:
        manager.connect()
        stats = manager.get_server_stats()
        if not stats:
            return "Failed to retrieve stats."
        return json.dumps(stats, indent=2)
    except Exception as e:
        return f"Stats Error: {e}"
    finally:
        manager.close()

if __name__ == "__main__":
    mcp.run()
