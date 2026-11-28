import json
from threading import Lock, Thread
from daemon import StreapRous, Response
from streaprous_socket.streaprous_raw_connection import (
    create_raw_socket,
    connect,
    run_conn_send,
    run_conn_recv,
    close_connection,
)

app = StreapRous()
raw_sock = None

tracker_addr = None
current_user = ""
peers = {}
connected_peers = set()
channels = ["connected"]
messages = []
peer_lock = Lock()


def send_request(method, host, port, path, payload=None, cookie=""):
    global raw_sock
    body = json.dumps(payload) if payload is not None else ""
    req = (
        "{} {} HTTP/1.1\r\n"
        "Host: {}:{}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: {}\r\n"
        "Cookie: {}\r\n"
        "Connection: close\r\n"
        "\r\n"
        "{}"
    ).format(method, path, host, port, len(body.encode("utf-8")), cookie, body)

    if raw_sock is None:
        raw_sock = create_raw_socket()
    conn_info = connect(raw_sock, app.ip, app.port, host, port)
    if conn_info is None:
        return ""
    run_conn_send(raw_sock, conn_info, req.encode("utf-8"))
    res = b""
    while True:
        chunk = run_conn_recv(raw_sock, conn_info)
        if not chunk:
            break
        res += chunk
    close_connection(raw_sock, conn_info)
    msg = res.decode("utf-8")
    parts = msg.split("\r\n\r\n", 1)

    return parts[1]


@app.route('/login/', methods=['POST'])
def login(headers="guest", body="anonymous"):
    print("[Peer] Send login to tracker {}".format(tracker_addr))
    info = json.loads(body)
    res = send_request("POST", tracker_addr[0], tracker_addr[1], "/login/", info)
    if res == "401 Unauthorized":
        return Response().build_unauthorized()

    res_data = json.loads(res)
    global current_user
    current_user = info.get("username", "")
    session_id = res_data.get("session_id", "")
    data = {"status": "ok"}

    cookie = "session_id={}; Path=/".format(session_id)
    return Response().build_cookie_response(json.dumps(data).encode("utf-8"), cookie)



@app.route('/submit-info/', methods=['POST'])
def submit_info(headers="guest", body="anonymous"):
    res = send_request("POST", tracker_addr[0], tracker_addr[1], "/submit-info/", {
        "ip": app.ip,
        "port": app.port,
        "channels": channels,
    }, headers.get("cookie", ""))
    return res.encode("utf-8")


@app.route('/add-list/', methods=['POST'])
def add_list(headers="guest", body="anonymous"):
    info = json.loads(body)
    if "channel" in info:
        ch = info["channel"]
        if ch and ch not in channels:
            channels.append(ch)
        send_request("POST", tracker_addr[0], tracker_addr[1], "/add-list/", {
            "ip": app.ip,
            "port": app.port,
            "channels": channels,
        }, headers.get("cookie", ""))
        return json.dumps({"status": "ok"}).encode("utf-8")

    peer_ip = info.get("ip")
    peer_port = info.get("port")
    with peer_lock:
        connected_peers.add((peer_ip, peer_port))
    return json.dumps({"status": "ok"}).encode("utf-8")


@app.route('/get-list/', methods=['GET'])
def get_list(headers="guest", body="anonymous"):
    res = send_request("GET", tracker_addr[0], tracker_addr[1], "/get-list/", cookie=headers.get("cookie", ""))
    if res == "401 Unauthorized":
        return Response().build_unauthorized()

    res_data = json.loads(res)
    with peer_lock:
        for p in res_data.get("peers", []):
            peers[(p["ip"], p["port"])] = p

    return json.dumps({
        "peers": list(peers.values()),
        "channels": channels,
        "messages": messages,
    }).encode("utf-8")


@app.route('/connect-peer/', methods=['POST'])
def connect_peer(headers="guest", body="anonymous"):
    info = json.loads(body)
    peer_ip = info.get("ip")
    peer_port = info.get("port")
    key = (peer_ip, peer_port)
    with peer_lock:
        connected_peers.add(key)
    send_request("POST", peer_ip, peer_port, "/add-list/", {
        "ip": app.ip,
        "port": app.port,
    })
    return json.dumps({"status": "ok"}).encode("utf-8")


@app.route('/send-peer/', methods=['POST'])
def send_peer(headers="guest", body="anonymous"):
    info = json.loads(body)
    if not (info.get("ip") == app.ip and info.get("port") == app.port):
        if (info["ip"], info["port"]) not in connected_peers:
            return Response().build_unauthorized()
        info["sender"] = current_user
        send_request("POST", info["ip"], info["port"], "/send-peer/", info)
    with peer_lock:
        messages.append(info)
    return json.dumps({"status": "ok"}).encode("utf-8")


def send_to_peer(peer, msg):
    if peer["ip"] == app.ip and peer["port"] == app.port:
        return
    data = dict(msg)
    data["ip"] = peer["ip"]
    data["port"] = peer["port"]
    send_request("POST", peer["ip"], peer["port"], "/send-peer/", data)


@app.route('/broadcast-peer/', methods=['POST'])
def broadcast_peer(headers="guest", body="anonymous"):
    info = json.loads(body)
    msg = {
        "sender": current_user,
        "channel": info.get("channel"),
        "text": info.get("text", ""),
    }
    with peer_lock:
        messages.append(msg)
        if msg["channel"] == "connected":
            targets = [peers[k] for k in connected_peers]
        else:
            targets = [p for p in peers.values() if msg["channel"] in p["channels"]]

    threads = [Thread(target=send_to_peer, args=(peer, msg)) for peer in targets]
    [t.start() for t in threads]
    [t.join() for t in threads]

    return json.dumps({"status": "ok"}).encode("utf-8")


def create_peer(ip, port, tracker):
    global tracker_addr
    tracker_addr = tracker
    app.prepare_address(ip, port)
    app.run()
