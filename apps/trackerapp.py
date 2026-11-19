#
# apps/trackerapp.py
# ~~~~~~~~~~~~~~~~~~
#
# Centralized Tracker Server for Peer-to-Peer Chat Application
#

import json
from daemon import StreapRous

app = StreapRous()

# ----------------- IN-MEMORY STORAGE -----------------
# Dynamically populated via API requests
USERS = {}      # Stores { username: password }
PEERS = {}      # Stores { username: {"ip": ip, "port": port} }
CHANNELS = {}   # Stores { channel_name: [username1, username2] }


# ----------------- TRACKER APIS -----------------

# API 1: User Login / Auto-Registration
@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user authentication. 
    Registers new users automatically or validates credentials for existing ones.
    """
    try:
        data = json.loads(body)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            res = {"status": "error", "message": "Missing username or password"}
        elif username not in USERS:
            # Auto-register new user
            USERS[username] = password
            print(f"[Tracker] Created new user: {username}")
            res = {"status": "success", "username": username, "message": "User registered and logged in"}
        elif USERS[username] == password:
            # Existing user with valid password
            res = {"status": "success", "username": username, "message": "Login successful"}
        else:
            # Existing user with invalid password
            res = {"status": "error", "message": "Invalid password"}
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


# API 2: Peer Registration (Submit P2P IP and Port)
@app.route('/submit-info', methods=['POST'])
def submit_info(headers="guest", body="anonymous"):
    """
    Register or update peer's listening IP and P2P port in the tracker directory.
    """
    try:
        data = json.loads(body)
        username = data.get("username")
        ip = data.get("ip")
        port = data.get("port")

        if not username or not ip or not port:
            res = {"status": "error", "message": "Missing required fields (username, ip, port)"}
        else:
            # Every registered peer joins the default channel "general"
            if username not in CHANNELS.setdefault("general", []):
                CHANNELS["general"].append(username)
            PEERS[username] = {
                "ip": ip,
                "port": int(port)
            }
            print(f"[Tracker] Registered peer: {username} -> {ip}:{port}")
            res = {"status": "success", "message": "Peer info registered successfully"}
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


# API 3: Channel Subscription (Join a chat channel)
@app.route('/add-list', methods=['POST'])
def add_list(headers="guest", body="anonymous"):
    """
    Add a user to a specific chat channel. Creates the channel if it does not exist.
    """
    try:
        data = json.loads(body)
        username = data.get("username")
        channel = data.get("channel", "general")

        if not username:
            res = {"status": "error", "message": "Missing username"}
        else:
            if channel not in CHANNELS:
                CHANNELS[channel] = []

            if username not in CHANNELS[channel]:
                CHANNELS[channel].append(username)

            print(f"[Tracker] User '{username}' joined channel '{channel}'")
            res = {
                "status": "success",
                "channel": channel,
                "members": CHANNELS[channel]
            }
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


# API 4: Peer Discovery (Retrieve active peers in a channel)
@app.route('/get-list', methods=['GET', 'POST'])
def get_list(headers="guest", body="anonymous"):
    """
    Fetch the list of active peers with their IP and port for P2P connection setup.
    """
    try:
        channel = "general"
        if body and body != "anonymous":
            try:
                data = json.loads(body)
                channel = data.get("channel", "general")
            except Exception:
                pass

        members = CHANNELS.get(channel, [])
        peer_list = []

        # Retrieve connection info for members who have registered their endpoints
        for user in members:
            if user in PEERS:
                peer_list.append({
                    "username": user,
                    "ip": PEERS[user]["ip"],
                    "port": PEERS[user]["port"]
                })

        res = {
            "status": "success",
            "channel": channel,
            "peers": peer_list
        }
    except Exception as e:
        res = {"status": "error", "message": f"Failed to retrieve list: {str(e)}"}

    return json.dumps(res).encode("utf-8")


def create_trackerapp(ip, port):
    """
    Prepare and launch the Tracker RESTful application.
    """
    app.prepare_address(ip, port)
    app.run()