import argparse

import json

from . import handler

def main():
    parser = argparse.ArgumentParser(description = 'verify AWS RDS DB snapshots.')
    parser.add_argument('config', help='The path to JSON config.')
    args = parser.parse_args()
    with open(args.config) as json_file:
        config = json.load(json_file)
    handler(config)

if __name__ == "__main__":
    main()
