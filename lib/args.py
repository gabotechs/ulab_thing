import argparse
import typing as T

parser = argparse.ArgumentParser()

parser.add_argument('--octoprint-url', default='http://localhost/api')
parser.add_argument('--ulab-backend-url', default="https://www.servidor3dulab.ovh")
parser.add_argument('--ulab-socket-url', default="wss://www.servidor3dulab.ovh/ws")
parser.add_argument('--ulab-token-path', default='/boot/ulab-token.txt')
parser.add_argument('--octoprint-upload-path', default='/home/pi/.octoprint/uploads')
parser.add_argument('--octoprint-config-path', default='/home/pi/.octoprint/config.yaml')


class Args:
    def __init__(self, parsed_args):
        self.octoprint_url: str = parsed_args.octoprint_url
        self.ulab_backend_url: str = parsed_args.ulab_backend_url
        self.ulab_socket_url: str = parsed_args.ulab_socket_url
        self.ulab_token_path: str = parsed_args.ulab_token_path
        self.octoprint_upload_path: str = parsed_args.octoprint_upload_path
        self.octoprint_config_path: str = parsed_args.octoprint_config_path


args: T.Union[Args, None] = None


def get_args() -> Args:
    global args
    if not args:
        args = Args(parser.parse_known_args()[0])
    return args
