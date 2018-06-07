#!/usr/bin/env python
"""Used to copy AWS RDS DB Instance or Cluster snapshots.

Copy to another region or just to keep snapshots around for
longer than the maximum of 35 days that RDS allows.
"""

import argparse
from datetime import datetime

import boto3

from dbsnap import (
    get_latest_snapshot,
    get_old_dbsnap_snapshots,
)

from dbsnap_copy import (
    parse_source,
    parse_destination,
    get_account_id,
    get_snapshot_target_name,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        help="The source of the snapshot in the format: "
        "<region>:<db-instance-identifier>",
    )
    parser.add_argument(
        "-d",
        "--dest",
        default=":",
        help="The destination of the snapshot in the format: "
        "[<region>]:[<new-snapshot-name>]). "
        "Defaults to the same region as source."
    )
    parser.add_argument(
        "--prune-old",
        type=int,
        help="If set, after the snapshot is taken, the command will clean up "
        "old snapshots, keeping around as many copies (the most recent) "
        "as you specify with this flag.",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="If set, do not actually change anything, just print out what "
        "would happen.",
    )
    parser.add_argument(
        "--kms-key",
        default=None,
        help="The KMS Key ID to use when copying the snapshot. Not necessary "
        "for most use-cases. See: http://docs.aws.amazon.com/AmazonRDS"
        "/latest/APIReference/API_CopyDBSnapshot.html",
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    source = parse_source(args.source)
    dest = parse_destination(source.region, args.dest)

    source_session = boto3.client("rds", region_name=source.region)
    dest_session = boto3.client("rds", region_name=dest.region)

    account_id = get_account_id()

    source_snapshot = get_latest_snapshot(
        source_session, source.id, snapshot_type="automated"
    )

    now = datetime.utcnow()
    target_snapshot_name = get_snapshot_target_name(
        dest, source_snapshot.id, source.region, now
    )

    msg = "[{}] Copying {} to {} in {}"
    print(msg.format(now, source_snapshot.arn, target_snapshot_name, dest.region))

    tags = {
        "source_snapshot_arn": source_snapshot.arn,
        "source_region": source_snapshot.region,
        "source_db_identifier": source_snapshot.id,
        "created_by": "dbsnap-copy",
    }

    if not args.dry_run:
        source_snapshot.copy(
            target_snapshot_name, dest_session=dest_session, tags=tags, kms_key=args.kms_key
        )

    if args.prune_old:
        old_snapshots = get_old_dbsnap_snapshots(
            dest_session, source.id, args.prune_old
        )
        msg = "[{}] Pruning {} old snapshots while keeping the most recent {}."
        print(msg.format(datetime.utcnow(), len(old_snapshots), args.prune_old))
        for snapshot in old_snapshots:
            print(
                "[{}] Deleting old snapshot: {}.".format(datetime.utcnow(), snapshot.id)
            )
            if not args.dry_run:
                snapshot.delete()


if __name__ == "__main__":
    main()
