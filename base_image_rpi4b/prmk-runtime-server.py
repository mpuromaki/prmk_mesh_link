#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import subprocess
import threading
import time
import json
import os
import glob
import configparser

PORT = 8080  # Runtime dashboard port (distinct from setup port)
CONFIG_DIR = "/etc/prmk"
FLAGS_DIR = "/etc/flags"

# ==========================================
# 1. APPLICATION REGISTRIES & HOOKS
# ==========================================
BACKGROUND_TASKS = []

def register_background_task(interval_seconds):
    """Decorator to register a periodic background function."""
    def decorator(func):
        def wrapper():
            while True:
                try:
                    func()
                except Exception as e:
                    print(f"Error in background task {func.__name__}: {e}")
                time.sleep(interval_seconds)
        BACKGROUND_TASKS.append(wrapper)
        return func
    return decorator


# ==========================================
# 2. BACKGROUND TASKS (Periodic jobs)
# ==========================================

@register_background_task(interval_seconds=86400) # Every 24 hours
def periodic_system_update_check():
    """Example background task: Check for system updates or trigger apt refresh."""
    print("[Background] Checking for system updates...")
    # Example: subprocess.run(['apt', 'update'], capture_output=True)
    pass

@register_background_task(interval_seconds=3600) # Every 1 hour
def periodic_infrastructure_sync():
    """Example background task: Pull latest trusted nodes/identities if allowed."""
    sync_allowed_path = os.path.join(FLAGS_DIR, "infrastructure_sync_allowed")
    if not os.path.exists(sync_allowed_path):
        return
    
    print("[Background] Syncing infrastructure data from mesh.prmk.fi...")
    # Add your curl/urllib fetching logic here to update /etc/prmk/trusted_nodes.json safely


# ==========================================
# 3. STARTUP INITIALIZATION HOOKS
# ==========================================
def run_startup_hooks():
    """Runs all configuration validations and hardware checks before starting the web server."""
    print("[Startup] Initializing PRMK Runtime Server...")
    
    # Ensure directories exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(FLAGS_DIR, exist_ok=True)
    
    # TODO: Add your custom startup hooks here
    # e.g., load_reticulum_config()
    # e.g., verify_hardware_interfaces()
    
    print("[Startup] All initialization checks completed successfully.")


# ==========================================
# 4. SYSTEM HELPER FUNCTIONS (Retculum & OS)
# ==========================================
def get_rnstatus_output():
    """Safely captures the output of the 'rnstatus' command."""
    try:
        result = subprocess.run(['rnstatus'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout
        else:
            return f"rnstatus exited with error: {result.stderr.strip()}"
    except FileNotFoundError:
        return "Reticulum (rnstatus) is not installed or not in PATH."
    except Exception as e:
        return f"Failed to execute rnstatus: {e}"

def get_reticulum_interfaces():
    """Parses Reticulum config files to extract configured interfaces."""
    interfaces = []
    # Reticulum standard config path check
    config_paths = glob.glob('/etc/reticulum/config') + glob.glob('/root/.reticulum/config')
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                config = configparser.ConfigParser()
                config.read(path)
                for section in config.sections():
                    if section.lower().startswith('interface'):
                        interfaces.append({
                            "name": section,
                            "type": config.get(section, 'type', fallback='Unknown'),
                            "mode": config.get(section, 'mode', fallback='Standard')
                        })
            except Exception as e:
                print(f"Error parsing Reticulum config at {path}: {e}")
                
    return interfaces

def load_local_json_data(filename):
    """Safely loads cached JSON files (trusted nodes/identities)."""
    file_path = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"error": "Failed to parse local configuration JSON."}
    return {"status": "Not configured or file missing."}


# ==========================================
# 5. HTTP WEB SERVER & UI ROUTER
# ==========================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRMK Node Management</title>
    <style>
        :root {
            --bg: #f4f6f9; --card: #ffffff; --text: #333; --primary: #2563eb; --border: #e5e7eb;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 1.5rem; color: #111827; }
        .card { background: var(--card); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h3 { margin-top: 0; color: #1f2937; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
        pre { background: #0f172a; color: #38bdf8; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }
        table { width: 100%%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
        th { color: #6b7280; }
        .badge { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>PRMK Appliance Dashboard</h1>
            <span class="badge">Running as Root</span>
        </header>

        <div class="card">
            <h3>Reticulum Network Status (rnstatus)</h3>
            <pre>{{RNSTATUS}}</pre>
        </div>

        <div class="card">
            <h3>Configured Reticulum Interfaces</h3>
            <table>
                <tr><th>Interface Name</th><th>Type</th><th>Mode</th></tr>
                {{INTERFACES_ROWS}}
            </table>
        </div>

        <div class="card">
            <h3>Trusted Nodes & Infrastructure Sync</h3>
            <pre>{{TRUSTED_NODES}}</pre>
        </div>
    </div>
</body>
</html>
"""

class RuntimeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/" or path == "/index.html":
            self.serve_dashboard()
        elif path == "/api/status":
            self.serve_json({
                "status": "healthy",
                "uptime": time.time(),
                "sync_allowed": os.path.exists(os.path.join(FLAGS_DIR, "infrastructure_sync_allowed"))
            })
        else:
            self.send_error(404, "Page Not Found")

    def serve_dashboard(self):
        # Gather live system data
        rnstatus_text = get_rnstatus_output()
        interfaces = get_reticulum_interfaces()
        trusted_nodes = load_local_json_data("trusted_nodes.json")

        # Build dynamic HTML rows for interfaces
        rows = ""
        if interfaces:
            for iface in interfaces:
                rows += f"<tr><td><strong>{iface['name']}</strong></td><td>{iface['type']}</td><td>{iface['mode']}</td></tr>"
        else:
            rows = "<tr><td colspan='3' style='color: #6b7280;'>No active Reticulum interfaces detected in config.</td></tr>"

        # Render template
        html = DASHBOARD_HTML.replace("{{RNSTATUS}}", rnstatus_text)
        html = html.replace("{{INTERFACES_ROWS}}", rows)
        html = html.replace("{{TRUSTED_NODES}}", json.dumps(trusted_nodes, indent=2))

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def serve_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        # Keep logs clean; suppress default verbose web requests
        pass


# ==========================================
# 6. MAIN APPLICATION ENTRYPOINT
# ==========================================
if __name__ == '__main__':
    # 1. Run startup hooks
    run_startup_hooks()

    # 2. Instantiate and start background task daemons
    print(f"[Runtime] Initializing {len(BACKGROUND_TASKS)} background task(s)...")
    for task in BACKGROUND_TASKS:
        t = threading.Thread(target=task, daemon=True)
        t.start()

    # 3. Start Main Web Server Loop
    with socketserver.TCPServer(("", PORT), RuntimeHandler) as httpd:
        print(f"[Runtime] PRMK Runtime Server active on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Runtime] Shutting down gracefully...")
            httpd.server_close()
