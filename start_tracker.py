#
# start_tracker.py
# ~~~~~~~~~~~~~~~~
#
# Entry point for deploying the Centralized Tracker Server process.
# Parses command-line arguments to configure the server IP address and port,
# then launches the tracker application.
#

import argparse
from apps import create_trackerapp

# Default port number for Tracker Server
DEFAULT_PORT = 8000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='TrackerServer',
        description='Start the Centralized Tracker Server for BTL1 CO3093/CO3094'
    )
    # Parse server IP and Port from command line (defaults to 0.0.0.0:8000)
    parser.add_argument('--server-ip', default='0.0.0.0', help='IP address to bind the server. Default is 0.0.0.0')
    parser.add_argument('--server-port', type=int, default=DEFAULT_PORT, help=f'Port number to bind. Default is {DEFAULT_PORT}')

    args = parser.parse_args()

    print("==================================================")
    print(f"[*] Starting Central Tracker on {args.server_ip}:{args.server_port}")
    print("[*] Supported APIs: /login, /submit-info, /add-list, /get-list")
    print("==================================================")

    # Launch the Tracker RESTful WebApp
    create_trackerapp(args.server_ip, args.server_port)