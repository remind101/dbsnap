import argparse

import json

from . import handler

from os import environ
import logging

log_level = environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger("dbsnap")
logger.setLevel(log_level)

from sys import stdout

ch = logging.StreamHandler(stdout)
ch.setLevel(log_level)
logger.addHandler(ch)


def main():
    parser = argparse.ArgumentParser(description="verify AWS RDS DB snapshots.")
    parser.add_argument(
        "config", type=argparse.FileType("r"), help="The path to JSON config."
    )
    args = parser.parse_args()
    with args.config as json_file:
        config = json.load(json_file)
    handler(config)


if __name__ == "__main__":
    main()
