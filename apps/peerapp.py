import json
from daemon import StreapRous
from daemon.httpadapter import HttpAdapter
from streaprous_socket.streaprous_raw_connection import (
    create_raw_socket,
    connect,
    run_conn_send,
    run_conn_recv,
    close_connection,
)

app = StreapRous()

# {"username": str, "ip": str, "port": int}
MY_INFO = {}

# { username: {"ip": ip, "port": port} }
CONNECTED_PEERS = {}

# [ {"sender": username, "message": text, "channel": channel} ]
MESSAGES = []

# {"ip": tracker_ip, "port": tracker_port}
TRACKER = {}

# Shared raw socket for outgoing connections (do not close after each request)
_RAW_SOCK = None


def _get_raw_socket():
    global _RAW_SOCK
    if _RAW_SOCK is None:
        _RAW_SOCK = create_raw_socket()
    return _RAW_SOCK


def send_tcp_direct(
    target_ip,
    target_port,
    payload,
    path="/send-peer",
    method="POST",
    cookie="",
    timeout=10.0,
):
    s = _get_raw_socket()
    conn_info = None

    try:
        conn_info = connect(
            s,
            server_ip=target_ip,
            server_port=int(target_port),
            client_port=MY_INFO["port"],
            client_ip=MY_INFO.get("ip", "0.0.0.0"),
            timeout=timeout,
        )

        adapter = HttpAdapter(None, None, None, None, None)
        body_str = json.dumps(payload) if payload is not None else ""
        status, resp_body = adapter.send_request(
            send=lambda data: run_conn_send(s, conn_info, data),
            read_more=lambda: run_conn_recv(s, conn_info),
            method=method,
            path=path,
            body=body_str,
            host=f"{target_ip}:{target_port}",
            cookie=cookie,
        )

        if 200 <= status < 300:
            return True, resp_body
        return False, f"HTTP {status}: {resp_body}"

    except Exception as e:
        return False, str(e)
    finally:
        if conn_info is not None:
            close_connection(s, conn_info)


@app.route("/connect-peer", methods=["POST"])
@app.route("/connect-peer/", methods=["POST"])
def connect_peer(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}
        username = data.get("username")
        ip = data.get("ip")
        port = data.get("port")

        if not username or not ip or not port:
            res = {"status": "error", "message": "Missing peer connection info"}
        else:
            CONNECTED_PEERS[username] = {"ip": ip, "port": int(port)}
            print(f"[Peer] Connected to peer: {username} ({ip}:{port})")
            res = {"status": "success", "message": f"Connected to {username}"}
    except Exception as e:
        res = {"status": "error", "message": str(e)}

    return json.dumps(res).encode("utf-8")


@app.route("/send-peer", methods=["POST"])
@app.route("/send-peer/", methods=["POST"])
def send_peer(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}

        if "sender" in data and "message" in data and "target_ip" not in data:
            sender = data.get("sender")
            msg = data.get("message")
            channel = data.get("channel", "general")

            MESSAGES.append({"sender": sender, "message": msg, "channel": channel})
            print(f"[Peer] Received message from '{sender}': {msg}")
            res = {"status": "success", "message": "Message delivered"}

        else:
            target_ip = data.get("target_ip")
            target_port = data.get("target_port")
            msg = data.get("message")
            channel = data.get("channel", "general")

            if not target_ip or not target_port or not msg:
                res = {
                    "status": "error",
                    "message": "Missing target_ip, target_port, or message",
                }
            else:
                payload = {
                    "sender": MY_INFO.get("username", "Anonymous"),
                    "message": msg,
                    "channel": channel,
                }

                success, err = send_tcp_direct(
                    target_ip, target_port, payload, path="/send-peer"
                )

                if success:
                    MESSAGES.append(payload)
                    print(f"[Peer] Sent message to {target_ip}:{target_port}")
                    res = {"status": "success", "message": "Message sent"}
                else:
                    print(f"[Peer] Failed to send to {target_ip}:{target_port}: {err}")
                    res = {"status": "error", "message": f"Delivery failed: {err}"}

    except Exception as e:
        res = {"status": "error", "message": str(e)}

    return json.dumps(res).encode("utf-8")


@app.route("/broadcast-peer", methods=["POST"])
@app.route("/broadcast-peer/", methods=["POST"])
def broadcast_peer(headers="guest", body="anonymous"):
    try:
        data = json.loads(body) if body and body != "anonymous" else {}
        msg = data.get("message")
        channel = data.get("channel", "general")
        peers = data.get("peers", [])

        if not msg:
            res = {"status": "error", "message": "Message cannot be empty"}
        else:
            payload = {
                "sender": MY_INFO.get("username", "Anonymous"),
                "message": msg,
                "channel": channel,
            }
            MESSAGES.append(payload)

            sent_count = 0
            for p in peers:
                p_ip = p.get("ip")
                p_port = int(p.get("port"))

                if p_ip == MY_INFO.get("ip") and p_port == MY_INFO.get("port"):
                    continue

                success, _ = send_tcp_direct(p_ip, p_port, payload, path="/send-peer")
                if success:
                    sent_count += 1

            print(f"[Peer] Broadcasted to {sent_count} peers in #{channel}")
            res = {"status": "success", "delivered_count": sent_count}

    except Exception as e:
        res = {"status": "error", "message": str(e)}

    return json.dumps(res).encode("utf-8")


def to_tracker(path, body):
    """Chuyen request cua giao dien sang tracker, tra ve body (str) cua tracker."""
    data = json.loads(body) if body else {}
    success, resp = send_tcp_direct(TRACKER["ip"], TRACKER["port"], data, path=path)
    if success:
        return resp
    return json.dumps({"status": "error", "message": resp})


@app.route("/login", methods=["POST"])
@app.route("/login/", methods=["POST"])
def login(headers="guest", body="anonymous"):
    data = json.loads(body) if body else {}
    if data.get("username") != MY_INFO["username"]:
        return json.dumps(
            {"status": "error", "message": "Login with this peer's username"}
        ).encode("utf-8")
    resp = to_tracker("/login", body)
    if json.loads(resp).get("status") == "success":
        return resp.encode("utf-8"), data["username"]
    return resp.encode("utf-8")


@app.route("/get-list", methods=["GET", "POST"])
@app.route("/get-list/", methods=["GET", "POST"])
def get_list(headers="guest", body="anonymous"):
    return to_tracker("/get-list", body).encode("utf-8")


@app.route("/add-list", methods=["POST"])
@app.route("/add-list/", methods=["POST"])
def add_list(headers="guest", body="anonymous"):
    return to_tracker("/add-list", body).encode("utf-8")


@app.route("/get-messages", methods=["GET"])
@app.route("/get-messages/", methods=["GET"])
def get_messages(headers="guest", body="anonymous"):
    return json.dumps({"status": "success", "messages": MESSAGES}).encode("utf-8")


def create_peerapp(
    ip, port, username="Anonymous", tracker_ip="127.0.0.1", tracker_port=9000
):
    MY_INFO["ip"] = ip
    MY_INFO["port"] = int(port)
    MY_INFO["username"] = username
    TRACKER["ip"] = tracker_ip
    TRACKER["port"] = int(tracker_port)

    reg_payload = {"username": username, "ip": ip, "port": int(port)}
    success, resp = send_tcp_direct(
        tracker_ip, tracker_port, reg_payload, path="/submit-info"
    )
    if success:
        print(f"[PeerApp] Auto-registered to tracker at {tracker_ip}:{tracker_port}")
    else:
        print(f"[PeerApp] Warning: Could not register to tracker: {resp}")

    print(f"[PeerApp] Starting Peer '{username}' on {ip}:{port}...")
    app.prepare_address(ip, port)
    app.run()
