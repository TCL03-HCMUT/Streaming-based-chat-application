"""Flow Control Module (Advertised Receive Window Management)."""
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .streaprous_raw_connection import conn_struct

DEFAULT_RCV_WND = 65535
DEFAULT_PROBE_INTERVAL = 5.0


def init_flow_control():
    return {
        'rwnd': DEFAULT_RCV_WND,
        'rcv_wnd': DEFAULT_RCV_WND,
        'last_probe_time': 0.0,
        'probe_interval': DEFAULT_PROBE_INTERVAL
    }

def update_peer_window(session: conn_struct, win_size: int):
    return session._replace(rwnd=max(0, int(win_size)))

def get_send_allowance(session) -> int:
    flight_size = session.server_seq - session.snd_una
    allowance = max(0, int(session.rwnd - flight_size))
    return allowance

def should_send_window_probe(session: conn_struct, current_time: float) -> bool:
    if session.rwnd == 0 and (current_time - session.last_probe_time) >= session.probe_interval:
        return True
    return False

def calculate_advertised_window(session: conn_struct, last_byte_read: int) -> int:
    last_byte_rcvd = session.client_seq
    buffer_used = max(0, last_byte_rcvd - last_byte_read)
    free_space = max(0, session.rcv_wnd - buffer_used)
    return min(free_space, 65535)