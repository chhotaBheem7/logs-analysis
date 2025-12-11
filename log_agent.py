import paramiko
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API keys from a .env file for security
load_dotenv()

def fetch_logs(hostname, username, key_filename, log_path, lines=200):
    """
    Connects to a remote server via SSH and fetches the last N lines of a log file.
    """
    try:
        print(f"🔌 Connecting to {hostname}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect using an SSH Key (Best Practice)
        client.connect(hostname, username=username, key_filename=key_filename)
        
        # Run 'tail' to get only the recent logs
        command = f"tail -n {lines} {log_path}"
        stdin, stdout, stderr = client.exec_command(command)
        
        logs = stdout.read().decode('utf-8')
        error_msg = stderr.read().decode('utf-8')
        
        client.close()
        
        if error_msg:
            print(f"⚠️ SSH Warning: {error_msg}")
            
        return logs
    except Exception as e:
        return f"CRITICAL_AGENT_ERROR: Could not fetch logs. Reason: {str(e)}"

def analyze_logs_with_gemini(log_data):
    """
    Sends raw log data to Gemini for error analysis.
    """
    # Configure Gemini
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash') # Flash is faster/cheaper for logs

    # The System Prompt
    prompt = f"""
    You are a Senior DevOps Engineer Agent. Analyze the following server logs.
    
    Your goal is to:
    1. Identify any "ERROR", "CRITICAL", or "Exception" entries.
    2. Ignore standard INFO/DEBUG noise.
    3. If an error is found, explain the ROOT CAUSE in simple terms.
    4. Suggest a potential fix for each error.

    Return the output in this format:
    - **Status**: [CRITICAL / WARNING / HEALTHY]
    - **Found Issues**: [List of issues or "None"]
    - **Analysis**: [Detailed explanation]
    - **Recommended Action**: [Actionable steps]

    LOG DATA:
    {log_data}
    """

    try:
        print("🧠 Sending logs to Gemini for analysis...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis Failed: {e}"

def main():
    # --- CONFIGURATION ---
    SERVER_IP = "192.168.1.10"       # Replace with your server IP
    SSH_USER = "ubuntu"              # Replace with your username
    SSH_KEY_PATH = "/path/to/key.pem" # Path to your private SSH key
    REMOTE_LOG_FILE = "/var/log/syslog" # Or /var/log/nginx/error.log
    # ---------------------

    # Step 1: Fetch
    print("running fetch...")
    logs = fetch_logs(SERVER_IP, SSH_USER, SSH_KEY_PATH, REMOTE_LOG_FILE)

    if not logs or "CRITICAL_AGENT_ERROR" in logs:
        print(logs)
        return

    # Step 2: Analyze
    print(f"Fetched {len(logs.splitlines())} lines of logs. Analyzing...")
    analysis = analyze_logs_with_gemini(logs)

    # Step 3: Report
    print("\\n" + "="*40)
    print("       🤖 GEMINI AGENT REPORT       ")
    print("="*40)
    print(analysis)

if __name__ == "__main__":
    main()
