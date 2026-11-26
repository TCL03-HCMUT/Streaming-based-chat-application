import argparse
from apps import create_trackerapp

DEFAULT_PORT = 9000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='TrackerServer', description='Central Tracker Daemon')
    parser.add_argument('--server-ip', default='0.0.0.0', help='IP address to bind the tracker')
    parser.add_argument('--server-port', type=int, default=DEFAULT_PORT, help='Port to listen on')

    args = parser.parse_args()
    create_trackerapp(args.server_ip, args.server_port)