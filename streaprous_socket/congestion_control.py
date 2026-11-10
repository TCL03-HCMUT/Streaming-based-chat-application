"""Congestion Control Module (TCP Reno: Slow Start, Congestion Avoidance, Fast Retransmit)."""

DEFAULT_MSS = 1460
DEFAULT_SSTHRESH = 65535


def init_congestion_control(initial_seq: int = 0, mss: int = DEFAULT_MSS):
    return {
        'cwnd': float(mss),
        'ssthresh': DEFAULT_SSTHRESH,
        'dup_acks': 0,
        'last_ack_seq': initial_seq,
        'mss': mss
    }


def on_ack_received(session, ack_seq: int):
    # TODO: Handle new ACK vs Duplicate ACK
    # If ack_seq > session.last_ack_seq:
    #   dup_acks = 0
    #   If cwnd < ssthresh (Slow Start):
    #     cwnd += mss
    #   Else (Congestion Avoidance):
    #     cwnd += mss * (mss / cwnd)
    #   last_ack_seq = ack_seq
    #
    # Elif ack_seq == session.last_ack_seq:
    #   dup_acks += 1
    #   If dup_acks == 3 (Trigger Fast Retransmit):
    #     ssthresh = max(int(cwnd / 2), 2 * mss)
    #     cwnd = ssthresh + 3 * mss
    #   Elif dup_acks > 3 (Fast Recovery):
    #     cwnd += mss
    pass


def on_timeout_detected(session):
    # TODO: Handle loss event from RTO timeout
    # ssthresh = max(int(cwnd / 2), 2 * mss)
    # cwnd = float(mss)
    # dup_acks = 0
    pass

