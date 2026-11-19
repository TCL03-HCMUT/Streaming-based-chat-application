#
# start_peer.py
# ~~~~~~~~~~~~~
#
# Entry point for deploying a Client Peer process.
# Each user (Alice, Bob, etc.) runs an instance of this process.
#

import argparse
from apps import create_peerapp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='PeerClient',
        description='Start a Client Peer process for BTL1 Hybrid Chat'
    )
    parser.add_argument('--username', required=True, help='Username of this peer (e.g. alice, bob)')
    parser.add_argument('--ui-port', type=int, default=5000, help='Port for Local WebApp (default: 5000)')
    parser.add_argument('--p2p-port', type=int, default=9001, help='Port for P2P Socket listening (default: 9001)')
    parser.add_argument('--bind-ip', default='127.0.0.1', help='IP address to bind (default: 127.0.0.1)')

    args = parser.parse_args()

    print("==================================================")
    print(f"[*] Starting Peer: {args.username}")
    print(f"[*] Local WebApp Port : {args.ui_port}")
    print(f"[*] P2P Listening Port: {args.p2p_port}")
    print("[*] Supported APIs    : /connect-peer, /send-peer, /broadcast-peer")
    print("==================================================")

    # Launch the peer node
    create_peerapp(
        ui_ip=args.bind_ip,
        ui_port=args.ui_port,
        p2p_ip=args.bind_ip,
        p2p_port=args.p2p_port,
        username=args.username
    )