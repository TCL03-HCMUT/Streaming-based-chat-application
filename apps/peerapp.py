#
# apps/peerapp.py
# ~~~~~~~~~~~~~~~
#
# Client Peer Node for Hybrid Peer-to-Peer Chat Application
#

import json
import socket
import threading
from daemon import StreapRous

app = StreapRous()

# ----------------- PEER STATE & IN-MEMORY STORAGE -----------------
# Current peer's username
CURRENT_USER = ""

# Active outgoing P2P sockets: { "target_username": socket_object }
CONNECTED_PEERS = {}

# Incoming chat history received via P2P sockets
MESSAGES = []


# ----------------- P2P LISTENER ENGINE -----------------
def start_p2p_listener(listen_ip, listen_port):
    """
    Background daemon thread that listens for incoming P2P connections from other peers.
    """
    listener_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        listener_sock.bind((listen_ip, listen_port))
        listener_sock.listen(10)
        print(f"[P2P Engine] Listening for incoming peer messages on {listen_ip}:{listen_port}...")
    except Exception as e:
        print(f"[P2P Engine] Failed to bind P2P port {listen_port}: {e}")
        return

    def handle_peer_connection(conn, addr):
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                payload = json.loads(data.decode("utf-8"))
                sender = payload.get("sender", "Unknown")
                message = payload.get("message", "")
                msg_type = payload.get("type", "direct")

                print(f"\n[P2P Received] ({msg_type}) From {sender}: {message}")
                MESSAGES.append(payload)
            except Exception:
                break
        conn.close()

    while True:
        try:
            conn, addr = listener_sock.accept()
            t = threading.Thread(target=handle_peer_connection, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            print(f"[P2P Engine] Accept error: {e}")
            break


# ----------------- 3 CORE PEER APIS -----------------

# API 1: Establish P2P Socket Connection to another Peer
@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers="guest", body="anonymous"):
    """
    Initiate a direct TCP P2P connection to a remote target peer.
    """
    try:
        data = json.loads(body)
        target_ip = data.get("ip") or data.get("peer_ip") or data.get("target_ip")
        target_port = data.get("port") or data.get("peer_port") or data.get("target_port")
        target_user = data.get("target_user") or data.get("username")

        if not target_ip or not target_port or not target_user:
            res = {"status": "error", "message": "Missing target connection parameters"}
        else:
            # Create a direct TCP socket connection to target peer
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((target_ip, int(target_port)))
            
            # Save socket into active dictionary
            CONNECTED_PEERS[target_user] = sock
            print(f"[Peer] Successfully established P2P socket with {target_user} ({target_ip}:{target_port})")

            res = {
                "status": "success",
                "message": f"Connected to peer {target_user}",
                "target_user": target_user
            }
    except Exception as e:
        res = {"status": "error", "message": f"Connection failed: {str(e)}"}

    return json.dumps(res).encode("utf-8")


# API 2: Send Direct 1-to-1 Message via P2P Socket
@app.route('/send-peer', methods=['POST'])
def send_peer(headers="guest", body="anonymous"):
    """
    Transmit a direct message to a specific peer over the established P2P socket.
    """
    try:
        data = json.loads(body)
        target_user = data.get("target_user") or data.get("receiver")
        message = data.get("message")
        sender = data.get("sender") or CURRENT_USER

        if not target_user or not message:
            res = {"status": "error", "message": "Missing target_user or message"}
        elif target_user not in CONNECTED_PEERS:
            res = {"status": "error", "message": f"Peer '{target_user}' is not connected yet. Call /connect-peer first."}
        else:
            payload = {
                "type": "direct",
                "sender": sender,
                "receiver": target_user,
                "message": message
            }
            # Send message data directly via socket (bypassing Tracker server)
            sock = CONNECTED_PEERS[target_user]
            sock.sendall(json.dumps(payload).encode("utf-8"))

            # Save to local messages
            MESSAGES.append(payload)
            print(f"[Peer Sent] Direct to {target_user}: {message}")
            res = {"status": "success", "message": "Message sent directly via P2P"}
    except Exception as e:
        res = {"status": "error", "message": f"Send error: {str(e)}"}

    return json.dumps(res).encode("utf-8")


# API 3: Broadcast Message to All Connected Peers in Channel
@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers="guest", body="anonymous"):
    """
    Broadcast a chat message to all connected peers in the channel via P2P sockets.
    """
    try:
        data = json.loads(body)
        message = data.get("message")
        channel = data.get("channel", "general")
        sender = data.get("sender") or CURRENT_USER

        if not message:
            res = {"status": "error", "message": "Missing message content"}
        else:
            payload = {
                "type": "broadcast",
                "sender": sender,
                "channel": channel,
                "message": message
            }
            raw_bytes = json.dumps(payload).encode("utf-8")

            # Iterate through all active peer sockets and transmit
            sent_count = 0
            for peer_name, sock in list(CONNECTED_PEERS.items()):
                try:
                    sock.sendall(raw_bytes)
                    sent_count += 1
                except Exception as err:
                    print(f"[Broadcast Error] Failed to send to {peer_name}: {err}")

            MESSAGES.append(payload)
            print(f"[Peer Broadcast] Channel '{channel}': {message} (sent to {sent_count} peers)")
            res = {
                "status": "success",
                "message": f"Broadcasted to {sent_count} peers",
                "sent_count": sent_count
            }
    except Exception as e:
        res = {"status": "error", "message": f"Broadcast error: {str(e)}"}

    return json.dumps(res).encode("utf-8")


def create_peerapp(ui_ip, ui_port, p2p_ip, p2p_port, username="anonymous"):
    """
    Initialize and launch both the P2P listener daemon and the local StreapRous WebApp.
    """
    global CURRENT_USER
    CURRENT_USER = username

    # 1. Start P2P socket listener in a background thread
    p2p_thread = threading.Thread(
        target=start_p2p_listener,
        args=(p2p_ip, p2p_port),
        daemon=True
    )
    p2p_thread.start()

    # 2. Start Local StreapRous WebApp (main thread)
    app.prepare_address(ui_ip, ui_port)
    app.run()