import json
import secrets
from threading import Lock
from daemon import StreapRous, Response

app = StreapRous()

users = {}
peers = {}
tracker_lock = Lock()


@app.route('/login/', methods=['POST'])
def login(headers="guest", body="anonymous"):
    print("[Tracker] Logging in {} to {}".format(headers, body))
    info = json.loads(body)
    username = info.get("username", "")
    password = info.get("password", "")
    if username not in users:
        users[username] = password
    if users[username] == password:
        with tracker_lock:
            session_id = secrets.token_hex(8)
            peers[session_id] = {"username": username}
        data = {"status": "ok", "session_id": session_id}
        return json.dumps(data).encode("utf-8")

    return Response().build_unauthorized()


@app.route('/submit-info/', methods=['POST'])
def submit_info(headers="guest", body="anonymous"):
    return add_list(headers, body)


@app.route('/add-list/', methods=['POST'])
def add_list(headers="guest", body="anonymous"):
    session_id = headers.get("cookies", {}).get("session_id")
    if session_id not in peers:
        return Response().build_unauthorized()

    info = json.loads(body)
    with tracker_lock:
        peers[session_id].update({
            "ip": info.get("ip"),
            "port": info.get("port"),
            "channels": info.get("channels"),
        })
    print("[Tracker] Add list:", peers)
    return json.dumps({"status": "ok"}).encode("utf-8")


@app.route('/get-list/', methods=['GET', 'POST'])
def get_list(headers="guest", body="anonymous"):
    session_id = headers.get("cookies", {}).get("session_id")
    if session_id not in peers:
        return Response().build_unauthorized()

    active_peers = [p for p in peers.values() if "ip" in p]
    print("[Tracker] Get list:", active_peers)
    return json.dumps({"status": "ok", "peers": active_peers}).encode("utf-8")


def create_tracker(ip, port):
    app.prepare_address(ip, port)
    app.run()
