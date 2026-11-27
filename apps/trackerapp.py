import json
from daemon import StreapRous

app = StreapRous()

USERS = {}  # { username: password }
PEERS = {}  # { username: {"ip": ip, "port": port} }
CHANNELS = {}  # { channel_name: [username1, username2] }


@app.route("/login", methods=["POST"])
@app.route("/login/", methods=["POST"])
def login(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            res = {"status": "error", "message": "Missing username or password"}
        elif username not in USERS:
            USERS[username] = password
            print(f"[Tracker] Created new user: {username}")
            res = {
                "status": "success",
                "username": username,
                "message": "User registered and logged in",
            }
        elif USERS[username] == password:
            res = {
                "status": "success",
                "username": username,
                "message": "Login successful",
            }
        else:
            res = {"status": "error", "message": "Invalid password"}
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


@app.route("/submit-info", methods=["POST"])
@app.route("/submit-info/", methods=["POST"])
def submit_info(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}
        username = data.get("username")
        ip = data.get("ip")
        port = data.get("port")

        if not username or not ip or not port:
            res = {
                "status": "error",
                "message": "Missing required fields (username, ip, port)",
            }
        else:
            if username not in CHANNELS.setdefault("general", []):
                CHANNELS["general"].append(username)
            PEERS[username] = {"ip": ip, "port": int(port)}
            print(f"[Tracker] Registered peer: {username} -> {ip}:{port}")
            res = {"status": "success", "message": "Peer info registered successfully"}
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


@app.route("/add-list", methods=["POST"])
@app.route("/add-list/", methods=["POST"])
def add_list(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}
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
                "members": CHANNELS[channel],
            }
    except Exception as e:
        res = {"status": "error", "message": f"Malformed request: {str(e)}"}

    return json.dumps(res).encode("utf-8")


@app.route("/get-list", methods=["GET", "POST"])
@app.route("/get-list/", methods=["GET", "POST"])
def get_list(headers="guest", body="anonymous"):
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

        for user in members:
            if user in PEERS:
                peer_list.append(
                    {
                        "username": user,
                        "ip": PEERS[user]["ip"],
                        "port": PEERS[user]["port"],
                    }
                )

        res = {"status": "success", "channel": channel, "peers": peer_list}
    except Exception as e:
        res = {"status": "error", "message": f"Failed to retrieve list: {str(e)}"}

    return json.dumps(res).encode("utf-8")


def create_trackerapp(ip, port):
    app.prepare_address(ip, port)
    app.run()
