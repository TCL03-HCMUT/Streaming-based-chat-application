"""Reliability Control Module (ARQ, Retransmission Queue, RTT/RTO Calculation)."""

import time

DEFAULT_RTO = 1.0


def init_reliability_control(initial_seq: int):
    return {
        'snd_una': initial_seq,
        'retrans_queue': [],  # list of dicts: [{'seq': int, 'payload': bytes, 'send_time': float}]
        'rcv_buffer': {},     # dict: {seq_num: payload_bytes} for out-of-order segments
        'rto': DEFAULT_RTO,
        'srtt': None,
        'rttvar': None
    }


def update_rtt_rto(session, sample_rtt: float):
    # TODO: Update SRTT, RTTVAR and RTO according to RFC 6298
    # If first measurement:
    #   SRTT = sample_rtt, RTTVAR = sample_rtt / 2
    # Else:
    #   RTTVAR = (1 - 0.25) * RTTVAR + 0.25 * abs(SRTT - sample_rtt)
    #   SRTT = (1 - 0.125) * SRTT + 0.125 * sample_rtt
    # RTO = max(1.0, SRTT + 4 * RTTVAR)
    return session


def prune_acknowledged_segments(session, ack_seq: int, current_time: float):
    # TODO: Remove segments where seq + len(payload) <= ack_seq from retrans_queue
    # Update session.snd_una to ack_seq
    # Compute sample RTT for fully acknowledged segments and update RTO
    new_queue = [seg for seg in session.retrans_queue if seg['seq'] + len(seg['payload']) > ack_seq]
    new_snd_una = max(session.snd_una, ack_seq)
    return session._replace(retrans_queue=new_queue, snd_una=new_snd_una)


def check_retransmission_timeout(session, current_time: float):
    # TODO: Inspect earliest packet in retrans_queue
    # If current_time - packet['send_time'] > session.rto:
    #   Apply Karn's exponential backoff: rto = min(60.0, session.rto * 2)
    #   Return (updated_session, packet_to_retransmit)
    # Else:
    #   Return (session, None)
    if session.retrans_queue:
        earliest = session.retrans_queue[0]
        if current_time - earliest['send_time'] > session.rto:
            new_rto = min(60.0, session.rto * 2.0)
            earliest['send_time'] = current_time
            return session._replace(rto=new_rto), earliest
    return session, None


def handle_incoming_data(session, pkt_seq: int, payload: bytes):
    """
    Handle in-order delivery, out-of-order handling (discard vs buffer), and cumulative ACK selection.
    
    Returns:
        tuple: (updated_session, deliverable_payload, ack_to_send)
    """
    expected_seq = session.client_seq
    rcv_buf = dict(session.rcv_buffer)
    deliverable = b""

    # TODO (Slide 71, 75, 88): Choose implementation strategy for out-of-order packets:
    #
    # Case 1: In-order data (pkt_seq == expected_seq)
    #   deliverable = payload
    #   expected_seq += len(payload)
    #   # If buffering is implemented: drain any consecutive buffered segments
    #   # while expected_seq in rcv_buf:
    #   #     chunk = rcv_buf.pop(expected_seq)
    #   #     deliverable += chunk
    #   #     expected_seq += len(chunk)
    #
    # Case 2: Out-of-order data (pkt_seq > expected_seq)
    #   - Option A (Discard, Slide 71): do nothing, drop payload
    #   - Option B (Buffer, Slide 75): rcv_buf[pkt_seq] = payload
    #   deliverable = b""
    #
    # Case 3: Duplicate data (pkt_seq < expected_seq)
    #   deliverable = b""

    if pkt_seq == expected_seq:
        deliverable = payload
        expected_seq += len(payload)

    updated_session = session._replace(
        client_seq=expected_seq,
        rcv_buffer=rcv_buf
    )
    return updated_session, deliverable, expected_seq


