import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--octoprint-url', default='http://localhost')
parser.add_argument('--ulab-url', required=True)
parser.add_argument('--user', required=True)
parser.add_argument('--password', required=True)
parser.add_argument('--octoprint-path', default='/home/pi/.octoprint')


class Args:
    def __init__(self, parsed_args):
        self.octoprint_url: str = parsed_args.octoprint_url
        self.ulab_url: str = parsed_args.ulab_url
        self.user: str = parsed_args.user
        self.password: str = parsed_args.password
        self.octoprint_path: str = parsed_args.octoprint_path


args: Args = None


def get_args() -> Args:
    global args
    if not args:
        args = Args(parser.parse_args())
    return args
