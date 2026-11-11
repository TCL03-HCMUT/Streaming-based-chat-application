"""Congestion Control Module (TCP Reno: Slow Start, Congestion Avoidance, Fast Retransmit)."""
from enum import Enum
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .streaprous_raw_connection import conn_struct

DEFAULT_MSS = 1460
DEFAULT_SSTHRESH = 65535

class CongestionPhase(Enum):
    SLOW_START = 1
    CONGESTION_AVOIDANCE = 2
    FAST_RECOVERY = 3

def init_congestion_control(initial_seq: int = 0, mss: int = DEFAULT_MSS):
    return {
        'cwnd': mss,
        'ssthresh': DEFAULT_SSTHRESH,
        'dup_acks': 0,
        'last_ack_seq': initial_seq,
        'mss': mss,
        'congestion_state': CongestionPhase.SLOW_START
    }


def on_ack_received(session: conn_struct, ack_seq: int):
    # TODO: Handle new ACK vs Duplicate ACK
    cwnd = session.cwnd
    ssthresh = session.ssthresh
    dup_acks = session.dup_acks
    last_ack = session.last_ack_seq
    mss = session.mss
    congestion_state = session.congestion_state
    new_state = congestion_state
    should_retransmit = False
    
    # New ACK
    if ack_seq > session.last_ack_seq:
        dup_acks = 0
        match congestion_state:
            case CongestionPhase.SLOW_START:
                cwnd += mss
                if cwnd >= ssthresh:
                    new_state = CongestionPhase.CONGESTION_AVOIDANCE
            case CongestionPhase.CONGESTION_AVOIDANCE:
                cwnd += mss * (mss / cwnd)
            case CongestionPhase.FAST_RECOVERY:
                cwnd = ssthresh
                new_state = CongestionPhase.CONGESTION_AVOIDANCE
        last_ack = ack_seq
    # Duplicate ACK
    # According to RFC 5681: DUPLICATE ACKNOWLEDGMENT: An acknowledgment is considered a
    # "duplicate" in the following algorithms when (a) the receiver of
    # the ACK has outstanding data, (b) the incoming acknowledgment
    # carries no data, (c) the SYN and FIN bits are both off, (d) the
    # acknowledgment number is equal to the greatest acknowledgment
    # received on the given connection (TCP.UNA from [RFC793]) and (e)
    # the advertised window in the incoming acknowledgment equals the
    # advertised window in the last incoming acknowledgment.
    elif ack_seq == last_ack and len(session.retrans_queue) > 0:
        if congestion_state == CongestionPhase.FAST_RECOVERY:
            cwnd += mss
        else:
            dup_acks += 1
            if dup_acks == 3:
                ssthresh = max(int(cwnd / 2), 2 * mss)
                cwnd = ssthresh + 3 * mss
                new_state = CongestionPhase.FAST_RECOVERY
                should_retransmit = True
                
    return session._replace(
        cwnd=cwnd, 
        ssthresh=ssthresh, 
        dup_acks=dup_acks, 
        last_ack_seq=last_ack, 
        congestion_state=new_state
    ), should_retransmit


def on_timeout_detected(session: conn_struct):
    cwnd = session.cwnd
    ssthresh = session.ssthresh
    dup_acks = session.dup_acks
    mss = session.mss
    
    ssthresh = max(int(cwnd / 2), 2 * mss)
    cwnd = mss
    dup_acks = 0
    return session._replace(cwnd=cwnd, ssthresh=ssthresh, dup_acks=dup_acks, congestion_state=CongestionPhase.SLOW_START)

