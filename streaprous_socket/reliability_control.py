from collections import namedtuple
import time

DEFAULT_TIMEOUT = 1.0
ALPHA = 0.125
BETA = 0.25


def init_reliability_control(initial_seq: int):
    return {
        'send_base': initial_seq,
        'unacked_queue': [],  # list of dicts: [{'seq': int, 'payload': bytes, 'send_time': float, 'is_retransmitted': bool}]
        'timeout_interval': DEFAULT_TIMEOUT, 
        'estimated_rtt': None,
        'deviation_rtt': None,

        'rcv_buffer': {},     # dict: {seq_num: payload_bytes} for out-of-order segments
    }


def update_rtt_and_timeout(session :namedtuple, sample_rtt: float): # -> sender
    ertt = session.estimated_rtt
    drtt = session.deviation_rtt

    if ertt is None:
        ertt = sample_rtt
        drtt = sample_rtt / 2
    else:
        ertt = (1 - ALPHA) * ertt + ALPHA * sample_rtt
        drtt = (1 - BETA) * drtt + BETA * abs(ertt - sample_rtt)

    to = ertt + 4 * drtt

    return session._replace(estimated_rtt=ertt, deviation_rtt=drtt, timeout_interval=to)

def handle_ack(session, ack_seq: int, current_time: float): # -> sender
   if ack_seq == session.send_base:
       return session, True
   
   if ack_seq < session.send_base:
       return session, False

   session = session._replace(send_base=ack_seq)
   q = session.unacked_queue
   last = None

   while q and q[0]['seq'] + len(q[0]['payload']) <= ack_seq:
       last = q.pop(0)

   if last is not None and last['is_retransmitted'] is False:
       sample_rtt = current_time - last['send_time']
       session = update_rtt_and_timeout(session, sample_rtt)

   if len(q) > 0:
       q[0]['send_time'] = time.time()

   return session, False

def check_and_handle_timeout(session, current_time: float): # -> sender

    if len(session.unacked_queue) == 0:
        return session, None

    oldest = session.unacked_queue[0]
    if current_time - oldest['send_time'] <= session.timeout_interval:
        return session, None

    oldest['is_retransmitted'] = True
    oldest['send_time'] = current_time

    return session, oldest




def handle_incoming_data(session, pkt_seq: int, payload: bytes): # -> receiver
    expected_seq = session.client_seq
    delivered_data = b""

    if pkt_seq < expected_seq:
        return session, delivered_data, expected_seq

    if pkt_seq > expected_seq:
        session.rcv_buffer[pkt_seq] = payload
        return session, delivered_data, expected_seq

    while pkt_seq == expected_seq:
        delivered_data += payload
        expected_seq += len(payload)

        if session.rcv_buffer.get(expected_seq, None) is not None:
            payload = session.rcv_buffer.pop(expected_seq)
            pkt_seq += len(payload)

        else:
            break

    return session._replace(client_seq=expected_seq), delivered_data, expected_seq


