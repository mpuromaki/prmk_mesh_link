#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import subprocess
import urllib.parse
import uuid
import socket
import time
import threading
import ssl
import pam

PORT = 443
CERT_DIR = "/etc/prmk"
CERT_PATH = os.path.join(CERT_DIR, "cert.pem")
KEY_PATH = os.path.join(CERT_DIR, "key.pem")

# --- Security & State Management ---
LOCK = threading.Lock()
ACTIVE_SESSION_TOKEN = None  
LAST_FAILED_LOGIN_TIME = 0.0
RATE_LIMIT_SECONDS = 3.0     

# --- SSL Certificate Management ---

def ensure_ssl_certificate():
    os.makedirs(CERT_DIR, exist_ok=True)
    regenerate = True

    if os.path.exists(CERT_PATH) and os.path.exists(KEY_PATH):
        try:
            result = subprocess.run(
                ['openssl', 'x509', '-checkend', '86400', '-noout', '-in', CERT_PATH],
                capture_output=True
            )
            if result.returncode == 0:
                regenerate = False
        except Exception:
            regenerate = True

    if regenerate:
        print("Generating fresh self-signed SSL certificate for PRMK Mesh Link...")
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-keyout', KEY_PATH, '-out', CERT_PATH,
                '-days', '365', '-nodes',
                '-subj', '/CN=prmk-mesh-link'
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("SSL certificate generated successfully.")
        except Exception as e:
            print(f"Error generating SSL certificate: {e}")

# --- System Utility Functions ---

def get_system_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        ips.append(f"Hostname: {hostname} ({local_ip})")
        
        result = subprocess.run(['ip', '-o', '-4', 'addr', 'show'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                if parts[1] != 'lo':
                    ips.append(f"{parts[1]}: {parts[4].split('/')[0]}")
    except Exception as e:
        ips.append(f"Error fetching IPs: {e}")
    return ips

def check_apt_upgradable():
    try:
        result = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        upgradable_count = max(0, len(lines) - 1)
        return {"status": "success", "upgradable": upgradable_count, "details": lines[1:]}
    except Exception as e:
        return {"status": "error", "message": str(e), "upgradable": 0}

def check_pip_reticulum():
    # Fast local version check without blocking outdated network queries
    try:
        installed = subprocess.run(['pip', 'show', 'rns'], capture_output=True, text=True)
        version_line = [l for l in installed.stdout.splitlines() if l.startswith('Version:')]
        curr_ver = version_line[0].split(':')[1].strip() if version_line else "Unknown"
        return {"installed": curr_ver}
    except Exception as e:
        return {"installed": "Unknown", "error": str(e)}

def authenticate_root(password):
    global LAST_FAILED_LOGIN_TIME
    
    with LOCK:
        now = time.time()
        if now - LAST_FAILED_LOGIN_TIME < RATE_LIMIT_SECONDS:
            return False, "Rate limited. Please wait a moment before trying again."

        try:
            p = pam.pam()
            if p.authenticate('root', password):
                return True, ""
            else:
                return False, "Invalid root password."
        except Exception as e:
            print(f"[Auth Exception] {e}")

        LAST_FAILED_LOGIN_TIME = time.time()
        return False, "Invalid root password."

# --- HTTP Request Handler ---

class PRMKHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return super().log_message(format, *args)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.serve_dashboard()
        elif path == '/api/status':
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
            
            status_data = {
                "ips": get_system_ips(),
                "apt": check_apt_upgradable(),
                "reticulum": check_pip_reticulum(),
                "reticulum_identity": "Loaded from ~/.reticulum/identity (Placeholder)",
                "connections_count": 3
            }
            self.send_json(status_data)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = {}
        if body:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = urllib.parse.parse_qs(body)

        if path == '/api/login':
            self.log_message("Authentication attempt for user: %s", "root")
            global ACTIVE_SESSION_TOKEN
            password = data.get('password', '')
            if isinstance(password, list): password = password[0]
            
            success, err_msg = authenticate_root(password)
            if success:
                self.log_message("Authentication successful for user: %s", "root")
                with LOCK:
                    new_token = str(uuid.uuid4())
                    ACTIVE_SESSION_TOKEN = new_token
                
                self.send_response(200)
                self.send_header('Set-Cookie', f'session={new_token}; Path=/; HttpOnly; Secure; SameSite=Strict')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            else:
                self.log_message("Authentication failed for user: %s", "root")
                self.send_json({"success": False, "error": err_msg}, 401)

        elif path == '/api/update/apt':
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
            try:
                subprocess.run(['apt-get', 'update'], check=True)
                subprocess.run(['apt-get', 'upgrade', '-y'], check=True)
                self.send_json({"success": True, "message": "System updated & upgraded successfully"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)

        elif path == '/api/update/pip':
            if not self.is_authenticated():
                self.send_json({"error": "Unauthorized"}, 401)
                return
            try:
                subprocess.run(['pip', 'install', '--upgrade', 'rns'], check=True)
                self.send_json({"success": True, "message": "Reticulum updated successfully"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)}, 500)
        else:
            self.send_error(404, "Not Found")

    def is_authenticated(self):
        global ACTIVE_SESSION_TOKEN
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session='):
                token = cookie.split('=', 1)[1].strip()
                with LOCK:
                    if ACTIVE_SESSION_TOKEN and token == ACTIVE_SESSION_TOKEN:
                        return True
        return False

    def send_json(self, data, code=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

    def serve_dashboard(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PRMK Mesh Link Runtime</title>
    <style>
        :root {
            --bg-base: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #fbbf24;
            --accent-hover: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { font-size: 1.25rem; font-weight: bold; color: var(--accent); }
        .auth-status { font-size: 0.875rem; color: var(--text-muted); }
        main {
            flex: 1;
            max-width: 64rem;
            width: 100%;
            margin: 0 auto;
            padding: 1.5rem;
        }
        .card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .max-w-md { max-width: 28rem; margin: 3rem auto; }
        .space-y-4 > * + * { margin-top: 1rem; }
        .space-y-6 > * + * { margin-top: 1.5rem; }
        label { display: block; font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem; }
        input[type="password"] {
            width: 100%;
            background-color: var(--bg-base);
            border: 1px solid var(--border-color);
            border-radius: 0.375rem;
            padding: 0.5rem 0.75rem;
            color: white;
            font-size: 1rem;
            outline: none;
        }
        input[type="password"]:focus { border-color: var(--accent); }
        button {
            width: 100%;
            background-color: var(--accent);
            color: #030712;
            font-weight: 600;
            padding: 0.625rem;
            border: none;
            border-radius: 0.375rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover { background-color: var(--accent-hover); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-secondary {
            background-color: #334155;
            color: white;
            width: auto;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
        }
        .btn-secondary:hover { background-color: #475569; }
        .error-msg { color: #f87171; font-size: 0.875rem; text-align: center; margin-top: 0.5rem; }
        .hidden { display: none !important; }
        .tabs { display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }
        .tab-btn {
            background: transparent;
            color: var(--text-muted);
            width: auto;
            padding: 0.5rem 1rem;
            font-weight: 500;
            border-radius: 0.375rem;
        }
        .tab-btn.active { background-color: var(--bg-card); color: var(--accent); }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
        .stat-val { font-size: 1.5rem; font-weight: bold; color: var(--accent); margin-top: 0.5rem; }
        .stat-mono { font-family: monospace; font-size: 0.875rem; color: #cbd5e1; word-break: break-all; margin-top: 0.5rem; }
        ul { list-style: none; }
        li { font-family: monospace; font-size: 0.875rem; color: #cbd5e1; padding: 0.25rem 0; }
        .flex-between { display: flex; justify-content: space-between; align-items: center; }
        .border-b { border-bottom: 1px solid var(--border-color); padding-bottom: 1rem; }
    </style>
</head>
<body>
    <header>
        <h1>PRMK Mesh Link</h1>
        <div id="auth-status" class="auth-status"></div>
    </header>

    <main>
        <!-- Login Modal / Card -->
        <div id="login-card" class="card max-w-md">
            <h2 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; text-align: center;">Root Authentication Required</h2>
            <form id="login-form" onsubmit="handleLogin(event)" class="space-y-4">
                <div>
                    <label>Root Password</label>
                    <input type="password" id="password" required>
                </div>
                <button type="submit" id="login-btn">Login</button>
                <p id="login-error" class="error-msg hidden"></p>
            </form>
        </div>

        <!-- Dashboard App View -->
        <div id="dashboard-app" class="hidden space-y-6">
            <!-- Tabs Navigation -->
            <div class="tabs">
                <button onclick="switchTab('home')" class="tab-btn active" data-target="home">Home</button>
                <button onclick="switchTab('system')" class="tab-btn" data-target="system">System</button>
                <button onclick="switchTab('interfaces')" class="tab-btn" data-target="interfaces">Interfaces</button>
            </div>

            <!-- Home Tab -->
            <div id="tab-home" class="tab-content space-y-4">
                <div class="grid-3">
                    <div class="card">
                        <div style="font-size: 0.875rem; color: var(--text-muted);">Active Connections</div>
                        <div id="stat-connections" class="stat-val">Loading...</div>
                    </div>
                    <div class="card" style="grid-column: span 2;">
                        <div style="font-size: 0.875rem; color: var(--text-muted);">Reticulum Identity</div>
                        <div id="stat-identity" class="stat-mono">Loading...</div>
                    </div>
                </div>
                <div class="card">
                    <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem;">Network Interfaces & IPs</div>
                    <ul id="stat-ips"></ul>
                </div>
            </div>

            <!-- System Tab -->
            <div id="tab-system" class="tab-content space-y-4 hidden">
                <div class="card space-y-4">
                    <h3 style="font-size: 1.125rem; font-weight: 600;">Software Updates</h3>
                    <div class="flex-between border-b">
                        <div>
                            <div style="font-weight: 500;">APT Package Upgrades</div>
                            <div id="apt-status-text" style="font-size: 0.875rem; color: var(--text-muted);">Checking...</div>
                        </div>
                        <button onclick="runAptUpdate()" class="btn-secondary">Update APT</button>
                    </div>
                    <div class="flex-between" style="padding-top: 0.5rem;">
                        <div>
                            <div style="font-weight: 500;">Reticulum (Pip) Version</div>
                            <div id="pip-status-text" style="font-size: 0.875rem; color: var(--text-muted);">Checking...</div>
                        </div>
                        <button onclick="runPipUpdate()" class="btn-secondary">Update Reticulum</button>
                    </div>
                </div>
            </div>

            <!-- Interfaces Tab -->
            <div id="tab-interfaces" class="tab-content space-y-4 hidden">
                <div class="card space-y-4">
                    <h3 style="font-size: 1.125rem; font-weight: 600;">Reticulum & Hardware Interfaces</h3>
                    <p style="font-size: 0.875rem; color: var(--text-muted);">Categorized interfaces view (Local, Managed, Internet, RNode templates) ready for expansion.</p>
                </div>
            </div>
        </div>
    </main>

    <script>
        async function checkSession() {
            try {
                const res = await fetch('/api/status', { credentials: 'include' });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('login-card').classList.add('hidden');
                    document.getElementById('dashboard-app').classList.remove('hidden');
                    document.getElementById('auth-status').innerText = 'Logged in as root';
                    populateDashboard(data);
                }
            } catch (e) {
                console.error("Session check error:", e);
            }
        }

        async function handleLogin(e) {
            e.preventDefault();
            const password = document.getElementById('password').value;
            const errEl = document.getElementById('login-error');
            const loginBtn = document.getElementById('login-btn');
            errEl.classList.add('hidden');
            
            loginBtn.disabled = true;
            loginBtn.innerText = 'Authenticating...';

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({password})
                });

                if (res.ok) {
                    // Instantly trigger session check & load dashboard without page reload lag
                    await checkSession();
                } else {
                    const data = await res.json();
                    errEl.innerText = data.error || 'Login failed';
                    errEl.classList.remove('hidden');
                    loginBtn.disabled = false;
                    loginBtn.innerText = 'Login';
                }
            } catch (err) {
                errEl.innerText = 'Network error or rate limited';
                errEl.classList.remove('hidden');
                loginBtn.disabled = false;
                loginBtn.innerText = 'Login';
            }
        }

        function populateDashboard(data) {
            document.getElementById('stat-connections').innerText = data.connections_count;
            document.getElementById('stat-identity').innerText = data.reticulum_identity;
            
            const ipList = document.getElementById('stat-ips');
            ipList.innerHTML = data.ips.map(ip => `<li>${ip}</li>`).join('');

            const aptText = data.apt.upgradable > 0 ? `${data.apt.upgradable} packages can be updated` : 'System is up to date';
            document.getElementById('apt-status-text').innerText = aptText;

            document.getElementById('pip-status-text').innerText = `Installed version: ${data.reticulum.installed}`;
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`tab-${tabName}`).classList.remove('hidden');
            document.querySelector(`[data-target="${tabName}"]`).classList.add('active');
        }

        async function runAptUpdate() {
            alert('Running apt update & upgrade... this may take a moment.');
            const res = await fetch('/api/update/apt', {method: 'POST', credentials: 'include'});
            const data = await res.json();
            alert(data.message || data.error);
            checkSession();
        }

        async function runPipUpdate() {
            alert('Updating Reticulum via pip...');
            const res = await fetch('/api/update/pip', {method: 'POST', credentials: 'include'});
            const data = await res.json();
            alert(data.message || data.error);
            checkSession();
        }

        checkSession();
    </script>
</body>
</html>"""
        response = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

def run():
    ensure_ssl_certificate()

    server_address = ('', PORT)
    httpd = socketserver.TCPServer(server_address, PRMKHandler)
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Starting PRMK Secure Runtime Server (HTTPS) on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == '__main__':
    run()
