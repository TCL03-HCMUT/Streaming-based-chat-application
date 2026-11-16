import time
import re
import socket
import json
from streaprous_socket.streaprous_raw_connection import connect, run_conn_send, run_conn_recv, close_connection
from streaprous_socket.streaprous_packet_dispatcher import register_port, unregister_port

def recv_full_http(raw_socket, conn_info, timeout=5.0) -> bytes:
    """
    Repeatedly calls run_conn_recv() until a complete HTTP message 
    (headers + Content-Length body) has arrived, or timeout expires.
    """
    buf = b""
    deadline = time.time() + timeout
    content_length = None
    while time.time() < deadline:
        chunk = run_conn_recv(raw_socket, conn_info)
        if not chunk:
            break   # Connection closed (FIN / RST)
        buf += chunk
        # 1. Look for end of headers
        if content_length is None and b"\r\n\r\n" in buf:
            head, _, _ = buf.partition(b"\r\n\r\n")
            m = re.search(rb"content-length:\s*(\d+)", head, re.IGNORECASE)
            if m:
                content_length = int(m.group(1))
            else:
                # If there's no Content-Length header (e.g. GET request), we only need headers
                break
        # 2. Check if the full body has arrived
        if content_length is not None:
            _, _, body = buf.partition(b"\r\n\r\n")
            if len(body) >= content_length:
                break   # Full HTTP message received!
    return buf

_global_raw_socket = None
_local_ip = None

def init_raw_client(s: socket.socket, local_ip: str):
    global _global_raw_socket, _local_ip
    _global_raw_socket = s
    _local_ip = local_ip

def http_raw_request(target_ip: str, target_port: int, method: str, path: str, data: dict = None, headers: dict = None, timeout: float = 6.0) -> dict:
    """
    Sends an HTTP request completely over StreapRous raw sockets:
    1. Active connect() handshake
    2. run_conn_send() HTTP payload
    3. run_conn_recv() response until Content-Length is satisfied
    4. close_connection()
    """
    global _global_raw_socket, _local_ip
    if not _global_raw_socket:
        raise RuntimeError("Raw client not initialized. Call init_raw_client first.")

    payload = json.dumps(data) if data is not None else ""
    req_str = (
        f"{method} {path} HTTP/1.1\r\n"
        f"Host: {target_ip}:{target_port}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        f"Connection: close\r\n"
    )
    if headers:
        for k, v in headers.items():
            req_str += f"{k}: {v}\r\n"
    req_str += "\r\n" + payload
    req_bytes = req_str.encode('utf-8')

    # 1. Active 3-way handshake over raw socket
    conn = connect(_global_raw_socket, _local_ip, target_ip, int(target_port), timeout=timeout)
    
    try:
        # 2. Transmit request using streaprous raw connection
        run_conn_send(_global_raw_socket, conn, req_bytes)
        
        resp_bytes = recv_full_http(_global_raw_socket, conn, timeout=timeout)
    finally:
        # 4. Clean up connection
        unregister_port(conn.server_port)
        close_connection(_global_raw_socket, conn)

    # Parse JSON
    header_part, _, body_part = resp_bytes.partition(b"\r\n\r\n")
    try:
        return json.loads(body_part.decode('utf-8'))
    except Exception:
        return {"raw": body_part.decode('utf-8', errors='ignore')}