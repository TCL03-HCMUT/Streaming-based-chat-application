import argparse
from apps import create_peerapp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='PeerNode', description='Peer-to-Peer Chat Daemon')
    parser.add_argument('--server-ip', default='0.0.0.0', help='Local IP to bind the peer webapp')
    parser.add_argument('--server-port', type=int, required=True, help='Local port for this peer (e.g. 9001)')
    parser.add_argument('--username', default='Anonymous', help='Display username for this peer')
    parser.add_argument('--tracker-ip', default='127.0.0.1', help='IP of the central tracker')
    parser.add_argument('--tracker-port', type=int, default=9000, help='Port of the central tracker')

    args = parser.parse_args()
    create_peerapp(
        ip=args.server_ip,
        port=args.server_port,
        username=args.username,
        tracker_ip=args.tracker_ip,
        tracker_port=args.tracker_port
    )