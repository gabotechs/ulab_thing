import argparse
import os
import json

parser = argparse.ArgumentParser()

parser.add_argument('--octoprint-url', default='http://localhost/api')
parser.add_argument('--ulab-url', required=True)
parser.add_argument('--ulab-token-path', default='/boot/ulab-token.txt')
parser.add_argument('--octoprint-path', default='/home/pi/.octoprint')


class Args:
    def __init__(self, parsed_args):
        override_args = {}
        if os.path.isfile("override_args.json"):
            try:
                override_args = json.load(open("override_args.json"))
            except Exception as e:
                print("error loading override args", e)

        self.octoprint_url: str = parsed_args.octoprint_url if "--octoprint-url" not in override_args else override_args["--octoprint-url"]
        self.ulab_url: str = parsed_args.ulab_url if "--ulab-url" not in override_args else override_args["--ulab-url"]
        self.ulab_token_path: str = parsed_args.ulab_token_path if "--ulab-token-path" not in override_args else override_args["--ulab-token-path"]
        self.octoprint_path: str = parsed_args.octoprint_path if "--octoprint-path" not in override_args else override_args["--octoprint-path"]


args: Args = None


def get_args() -> Args:
    global args
    if not args:
        args = Args(parser.parse_args())
    return args
