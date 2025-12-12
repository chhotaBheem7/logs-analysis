import paramiko
import os
from time import sleep

class DeploymentManager:
    def __init__(self, hostname, username, key_filename):
        self.hostname = hostname
        self.username = username
        self.key_filename = key_filename
        self.ssh_client = None

    def connect(self):
        """Establishes an SSH connection."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"🔌 Connecting to {self.hostname}...")
            self.ssh_client.connect(
                self.hostname, 
                username=self.username, 
                key_filename=self.key_filename
            )
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def run_command(self, command, sudo=False):
        """Runs a shell command on the remote server."""
        if not self.ssh_client:
            raise Exception("SSH Client not connected.")
        
        if sudo:
            command = f"sudo {command}"
        
        print(f"Exec: {command}")
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        
        # Stream output in real-time? For now, just wait.
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        
        if exit_status != 0:
            print(f"⚠️ Command Error ({exit_status}): {err}")
            return False, err
        return True, out

    def install_java(self, version=17):
        """Installs OpenJDK if not present."""
        print(f"🔍 Checking for Java {version}...")
        success, out = self.run_command("java -version")
        
        if success and f"version \"{version}" in out:
            print("✅ Java is already installed.")
            return True

        print("📦 Installing Java...")
        # Update apt and install default-jdk or specific version
        self.run_command("apt-get update", sudo=True)
        success, err = self.run_command(f"apt-get install -y openjdk-{version}-jdk", sudo=True)
        
        if success:
            print("✅ Java installed successfully.")
            return True
        return False

    def deploy_jar(self, local_jar_path, app_name, app_port=8080):
        """SCPs the JAR and sets up a systemd service."""
        remote_dir = f"/opt/{app_name}"
        remote_jar = f"{remote_dir}/{app_name}.jar"
        service_file = f"/etc/systemd/system/{app_name}.service"

        # 1. Create Directory
        self.run_command(f"mkdir -p {remote_dir}", sudo=True)
        self.run_command(f"chown {self.username}:{self.username} {remote_dir}", sudo=True)

        # 2. Upload JAR
        print(f"🚀 Uploading {local_jar_path} to {remote_jar}...")
        sftp = self.ssh_client.open_sftp()
        sftp.put(local_jar_path, remote_jar)
        sftp.close()

        # 3. Create Systemd Service
        print("⚙️ Configuring systemd service...")
        service_content = f"""[Unit]
Description={app_name} Service
After=network.target

[Service]
User={self.username}
ExecStart=/usr/bin/java -jar {remote_jar}
SuccessExitStatus=143
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        # Write temp file and move it (sudo restriction on sftp)
        temp_service = f"/tmp/{app_name}.service"
        # Escape newlines for echo
        clean_content = service_content.replace('\n', '\\n')
        self.run_command(f"echo -e '{clean_content}' > {temp_service}")
        self.run_command(f"mv {temp_service} {service_file}", sudo=True)
        self.run_command("systemctl daemon-reload", sudo=True)

        # 4. Restart Service
        print("🔄 Restarting service...")
        self.run_command(f"systemctl restart {app_name}", sudo=True)
        self.run_command(f"systemctl enable {app_name}", sudo=True)

        # 5. Health Check
        print("🏥 Waiting for service to start...")
        for _ in range(12): # Wait up to 60s
            sleep(5)
            # Use curl locally on the box to check port
            success, _ = self.run_command(f"curl -s localhost:{app_port} > /dev/null")
            if success:
                print("✅ Service is UP!")
                return True
        
        return False

    def get_server_stats(self):
        """Fetches CPU, Memory, and Disk usage."""
        stats = {}
        
        # 1. Memory (free -m)
        success, out = self.run_command("free -m | grep Mem | awk '{print $3 \"/\" $2}'")
        if success:
            used, total = out.split('/')
            stats['memory_used_mb'] = int(used)
            stats['memory_total_mb'] = int(total)
            stats['memory_percent'] = round((int(used)/int(total))*100, 1)

        # 2. CPU Load (uptime)
        success, out = self.run_command("uptime | awk -F'load average:' '{ print $2 }'")
        if success:
            stats['cpu_load_1min'] = out.split(',')[0].strip()

        # 3. Disk Usage (df -h /)
        success, out = self.run_command("df -h / | awk 'NR==2 {print $5}'")
        if success:
            stats['disk_usage_percent'] = out.strip()
            
        return stats

    def close(self):
        if self.ssh_client:
            self.ssh_client.close()
