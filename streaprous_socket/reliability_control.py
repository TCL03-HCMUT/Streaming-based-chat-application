from collections import namedtuple
from operator import is_
import time

DEFAULT_TIMEOUT = 1.0
ALPHA = 0.125
BETA = 0.25


def init_reliability_control(initial_seq: int, initial_):
    return {
        'send_base': initial_seq,
        'unacked_queue': [],  # list of dicts: [{'seq': int, 'payload': bytes, 'send_time': float}]
        'timeout_interval': DEFAULT_TIMEOUT, 
        'estimated_rtt': None,
        'deviation_rtt': None,
        'rcv_buffer': {},     # dict: {seq_num: payload_bytes} for out-of-order segments
    }


def update_rtt_and_timeout(session :namedtuple, sample_rtt: float):
    ertt = session['estimated_rtt']
    drtt = session['deviation_rtt']

    if ertt is None:
        ertt = sample_rtt
        drtt = sample_rtt / 2
    else:
        ertt = (1 - ALPHA) * ertt + ALPHA * sample_rtt
        drtt = (1 - BETA) * drtt + BETA * abs(ertt - sample_rtt)

    to = ertt + 4 * drtt

    return session._replace({'estimated_rtt': ertt, 'deviation_rtt': drtt, 'timeout_interval': to,})

def prune_acked_segments(session, ack_seq: int, current_time: float): # ten nay ko phu hop
   q = session.unack_queue
   while q[0].seq + len(q[0].payload) < ack_seq:
       del q[0]
   session.send_base = ack_seq
   sample_rtt = current_time - q[0].send_time
   session = update_rtt_and_timeout(session, sample_rtt)
   return session

def check_timeout(session, current_time: float):

    if current_time - session.unacked_queue[0]['send_time'] > session.timeout_interval:
        session.timeout_interval *= 2
        return session, session.unacked_queue[0]
    else:
        return session, None



def handle_incoming_data(session, pkt_seq: int, payload: bytes):
    expected_seq = session.client_seq
    data = b""

    if pkt_seq < expected_seq:
        return session, data, expected_seq

    if pkt_seq > expected_seq:
        session.rcv_buffer[pkt_seq] = payload
        return session, data, expected_seq

    while pkt_seq == expected_seq:
        data += payload
        expected_seq += len(payload)

        if session.rcv_buffer.get(expected_seq, None) is not None:
            payload = session.rcv_buffer.pop(expected_seq)
        else:
            break

    return session._replace(client_seq=expected_seq), data, expected_seq


