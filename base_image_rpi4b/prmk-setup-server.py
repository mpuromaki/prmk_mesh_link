#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import subprocess
import os
import threading
import time

PORT = 80

# Clean, modern CSS layout with descriptions (No JavaScript required)
HTML_FORM = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>First-Time Setup</title>
    <style>
        :root {
            --bg-color: #f4f6f9;
            --card-bg: #ffffff;
            --text-color: #333333;
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --border-color: #d1d5db;
            --desc-color: #6b7280;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            width: 100%;
            max-width: 480px;
        }
        h2 {
            margin-top: 0;
            color: #111827;
            font-size: 1.5rem;
            text-align: center;
        }
        p.subtitle {
            text-align: center;
            color: var(--desc-color);
            font-size: 0.9rem;
            margin-bottom: 24px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 0.95rem;
        }
        .description {
            font-size: 0.8rem;
            color: var(--desc-color);
            margin-bottom: 6px;
            line-height: 1.4;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        .checkbox-group {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-top: 10px;
        }
        .checkbox-group input {
            margin-top: 3px;
            width: 18px;
            height: 18px;
        }
        .checkbox-group label {
            font-weight: normal;
            font-size: 0.9rem;
            margin-bottom: 0;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-top: 10px;
        }
        button:hover {
            background-color: var(--primary-hover);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>PRMK Mesh Link First-Time Setup</h2>
        <p class="subtitle">Configure your device parameters to finalize deployment.</p>
        
        <form method="POST" action="/">
            <div class="form-group">
                <label for="root_password">New Root Password</label>
                <div class="description">Root password is required to administrate the system. No-one knows it but you. Store it safely. Minimum of 8 characters.</div>
                <input type="password" id="root_password" name="root_password" required minlength="8" placeholder="••••••••">
            </div>

            <div class="form-group">
                <label for="wifi_ssid">Wi-Fi Network Name (SSID)</label>
                <div class="description">The local wifi network Mesh Link should connect to. Mesh Link will provide Reticulum access to devices in this network. Mesh Link will use this network for automated updates.</div>
                <input type="text" id="wifi_ssid" name="wifi_ssid" required placeholder="MyHomeNetwork">
            </div>

            <div class="form-group">
                <label for="wifi_password">Wi-Fi Password</label>
                <div class="description">The security key for your specified Wi-Fi network.</div>
                <input type="password" id="wifi_password" name="wifi_password" required placeholder="••••••••">
            </div>

            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="infra_allowed" name="infra_allowed" value="yes" checked>
                    <label for="infra_allowed">
                        <strong>Allow PRMK Infrastructure Link</strong>
                        <div class="description" style="margin-top: 2px;">If allowed, list of Reticulum nodes is fetched from PRMK infrastructures for bootstrapping connectivity. PRMK public identity will be set as trusted, so that list of nodes can automatically update. PRMK will not have any control over your device. You can change settings any time.</div>
                    </label>
                </div>
            </div>

            <button type="submit">Apply Settings & Restart</button>
        </form>
    </div>
</body>
</html>
"""

HTML_SUCCESS = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings Applied</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #fff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            text-align: center;
            max-width: 400px;
        }
        h2 { color: #2563eb; margin-top: 0; }
        p { color: #6b7280; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Thank You!</h2>
        <p>The settings are being applied. The device will automatically restart when complete.</p>
        <p style="font-size: 0.85rem; margin-top: 20px;">You can close this window and disconnect from the setup hotspot.</p>
    </div>
</body>
</html>
"""

class SetupHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_FORM.encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        params = urllib.parse.parse_qs(post_data.decode('utf-8'))
        
        root_pw = params.get('root_password', [''])[0]
        ssid = params.get('wifi_ssid', [''])[0]
        password = params.get('wifi_password', [''])[0]
        infra_allowed = 'infra_allowed' in params

        # Send confirmation page to browser immediately
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_SUCCESS.encode("utf-8"))

        # Hand off execution to background worker so the browser response finishes cleanly
        threading.Thread(
            target=apply_settings_and_reboot, 
            args=(root_pw, ssid, password, infra_allowed)
        ).start()

    def log_message(self, format, *args):
        # Suppress heavy console request logs
        pass

def apply_settings_and_reboot(root_pw, ssid, password, infra_allowed):
    # Short pause to ensure the browser has finished reading the HTTP socket response
    time.sleep(3)
    
    # Change root password
    if root_pw:
        try:
            subprocess.run(['chpasswd'], input=f"root:{root_pw}".encode(), check=True)
            print("Root password successfully updated.")
        except Exception as e:
            print(f"Error updating root password: {e}")

    # Setup client Wi-Fi connection using NetworkManager (nmcli)
    if ssid and password:
        try:
            print(f"Connecting to Wi-Fi SSID: {ssid}")
            subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password], check=True)
            print("Successfully connected to Wi-Fi.")
        except Exception as e:
            print(f"Error connecting to Wi-Fi: {e}")

    # Handle infrastructure sync flag
    os.makedirs('/etc/flags', exist_ok=True)
    os.makedirs('/etc/prmk', exist_ok=True)
    
    if infra_allowed:
        with open('/etc/flags/infrastructure_sync_allowed', 'w') as f:
            f.write('true')
        print("Infrastructure sync flag enabled.")

        # Fetch trusted nodes from remote server
        api_url = "https://mesh.prmk.fi/api/trusted-nodes"
        try:
            print(f"Fetching trusted nodes from {api_url}...")
            req = urllib.request.Request(
                api_url, 
                headers={"User-Agent": "PRMK-Mesh-Link-Setup/0.1"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    # Validate that it's valid JSON before saving
                    parsed_json = json.loads(data)
                    
                    with open('/etc/prmk/trusted_nodes.json', 'w') as f:
                        json.dump(parsed_json, f, indent=2)
                    print("Trusted nodes successfully saved to /etc/prmk/trusted_nodes.json")
                else:
                    print(f"Failed to fetch trusted nodes. HTTP Status: {response.status}")
        except Exception as e:
            print(f"Error fetching trusted nodes (continuing setup anyway): {e}")

        # Fetch trusted identities (discovery & blackhole sources)
        identities_url = "https://mesh.prmk.fi/api/trusted-identities"
        try:
            print(f"Fetching trusted identities from {identities_url}...")
            req = urllib.request.Request(identities_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    identities_data = json.loads(response.read().decode('utf-8'))
                    with open('/etc/prmk/trusted_identities.json', 'w') as f:
                        json.dump(identities_data, f, indent=2)
                    print("Trusted identities successfully saved to /etc/prmk/trusted_identities.json")
                else:
                    print(f"Failed to fetch trusted identities. HTTP Status: {response.status}")
        except Exception as e:
            print(f"Error fetching trusted identities (continuing setup): {e}")

    # Create first-time setup complete flag (Prevents hotspot & server from running on next boot)
    with open('/etc/flags/first_time_setup_complete', 'w') as f:
        f.write('done')
    print("First time setup flag created.")

    # Trigger full system reboot
    print("Restarting system...")
    subprocess.run(['reboot'])

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), SetupHandler) as httpd:
        print(f"PRMK setup server running on port {PORT}...")
        httpd.serve_forever()
