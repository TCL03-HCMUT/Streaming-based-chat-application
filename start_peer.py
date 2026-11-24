import argparse
import sys

from apps.peer import create_peer
def main(ip, port, tracker_address):
    create_peer(ip, port, tracker_address)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Peer', description='', epilog='Peer daemon')
    parser.add_argument('--server-ip', '--ip', required=True)
    parser.add_argument('--server-port', '--port', type=int, required=True)
    parser.add_argument('--tracker-ip', required=True)
    parser.add_argument('--tracker-port', type=int, default=9000)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    tracker_address = (args.tracker_ip, args.tracker_port)

    sys.exit(main(ip, port, tracker_address))
