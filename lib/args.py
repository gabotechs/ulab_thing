import argparse
import os
import json

parser = argparse.ArgumentParser()

#### LEGACY ARGS ####
parser.add_argument('--ulab-url', default="https://www.servidor3dulab.ovh/v2")
parser.add_argument('--octoprint-path', default='/home/pi/.octoprint')
#####################
parser.add_argument('--octoprint-url', default='http://localhost/api')
parser.add_argument('--ulab-backend-url', default="https://www.servidor3dulab.ovh/v2")
parser.add_argument('--ulab-socket-url', default="https://www.servidor3dulab.ovh/v2/socket")
parser.add_argument('--ulab-token-path', default='/boot/ulab-token.txt')
parser.add_argument('--octoprint-upload-path', default='/home/pi/.octoprint/uploads')
parser.add_argument('--octoprint-config-path', default='/home/pi/.octoprint/config.yaml')


class Args:
    def __init__(self, parsed_args):
        override_args = {}
        if os.path.isfile("../override_args.json"):
            try:
                override_args = json.load(open("../override_args.json"))
                print("overriding args", override_args)
            except Exception as e:
                print("error loading override args", e)

        self.octoprint_url: str = parsed_args.octoprint_url if "--octoprint-url" not in override_args else override_args["--octoprint-url"]
        self.ulab_url: str = parsed_args.ulab_url if "--ulab-url" not in override_args else override_args["--ulab-url"]
        self.ulab_backend_url: str = parsed_args.ulab_backend_url if "--ulab-backend-url" not in override_args else override_args["--ulab-backend-url"]
        self.ulab_socket_url: str = parsed_args.ulab_socket_url if "--ulab-socket-url" not in override_args else override_args["--ulab-socket-url"]
        self.ulab_token_path: str = parsed_args.ulab_token_path if "--ulab-token-path" not in override_args else override_args["--ulab-token-path"]
        self.octoprint_path: str = parsed_args.octoprint_path if "--octoprint-path" not in override_args else override_args["--octoprint-path"]
        self.octoprint_upload_path: str = parsed_args.octoprint_upload_path if "--octoprint-upload-path" not in override_args else override_args["--octoprint-upload-path"]
        self.octoprint_config_path: str = parsed_args.octoprint_config_path if "--octoprint-config-path" not in override_args else override_args["--octoprint-config-path"]


args: Args = None


def get_args() -> Args:
    global args
    if not args:
        args = Args(parser.parse_known_args()[0])
    return args
