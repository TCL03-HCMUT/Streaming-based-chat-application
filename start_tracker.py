import argparse
import sys

from apps.tracker import create_tracker
def main(ip, port):
    create_tracker(ip, port)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Tracker', description='', epilog='Tracker daemon')
    parser.add_argument('--server-ip', '--ip', required=True)
    parser.add_argument('--server-port', '--port', type=int, default=9000)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    sys.exit(main(ip, port))
