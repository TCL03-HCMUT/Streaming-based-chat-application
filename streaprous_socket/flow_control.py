"""Flow Control Module (Advertised Receive Window Management)."""

DEFAULT_RCV_WND = 65535
DEFAULT_PROBE_INTERVAL = 5.0


def init_flow_control():
    return {
        'rwnd': DEFAULT_RCV_WND,
        'rcv_wnd': DEFAULT_RCV_WND,
        'last_probe_time': 0.0,
        'probe_interval': DEFAULT_PROBE_INTERVAL
    }


def update_peer_window(session, win_size: int):
    # TODO: Update peer's advertised receive window (rwnd) from incoming TCP header
    pass


def get_send_allowance(session) -> int:
    # TODO: Calculate allowable bytes to transmit based on flow control window
    # flight_size = session.server_seq - session.snd_una
    # allowance = max(0, session.rwnd - flight_size)
    pass


def should_send_window_probe(session, current_time: float) -> bool:
    # TODO: Probing
    # When peer advertises rwnd == 0, sender must periodically probe to avoid deadlock.
    # Check if:
    #   1. session.rwnd == 0
    #   2. (current_time - session.last_probe_time) >= session.probe_interval
    pass

