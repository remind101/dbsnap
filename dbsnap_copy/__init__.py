from collections import namedtuple
import string
import re

Source = namedtuple("Source", ["region", "id"])
Dest = namedtuple("Dest", ["region", "name"])

RE_UNSAFE = re.compile(r"[^a-zA-Z0-9-]")
RE_DEDUPE = re.compile(r"-+")


def parse_source(source):
    """Parse a source in the format <region>:<db-identifier>

    Args:
        source (str): The source string

    Returns:
        :class:`Source`: A Source namedtuple.
    """
    try:
        region, _id = source.split(":", 1)
    except ValueError:
        raise ValueError(
            "Pass source like this <region>:<db-identifier> not `{}`.".format(source)
        )

    return Source(region, _id)


def parse_destination(source_region, d=":"):
    """Parse a destination in the format <region>:<snapshot-name>

    Args:
        source_region (str): The region of the source instance.
        d (str): The destination string

    Returns:
        :class:`Dest`: The destination.
    """
    try:
        r, s = d.split(":", 1)
    except ValueError:
        raise ValueError(
            "Dest {} not in [<region>]:[<db-instance-identifier>] form.".format(d)
        )
    region = r or source_region
    snapshot_name = s or None

    return Dest(region, snapshot_name)


def get_account_id():
    """Returns the AWS Account ID for the provided credentials."""
    import boto3

    session = boto3.client("iam", region_name="us-east-1")
    first_arn = session.list_users()["Users"][0]["Arn"]
    return first_arn.split(":")[4]


def sanitize_snapshot_name(*args):
    """
    Accept any number of str args.
    Join and sanitize the result to form a safe snapshot name.

    >>> make_env_var_name('prod_api-db_copy:test$_db-to-us-west-1')
    'prod-api-db-copy-test-db-to-us-west-1'
    """
    subject = "-".join(args)
    return RE_DEDUPE.sub("-", RE_UNSAFE.sub("-", subject))


def get_snapshot_target_name(dest, source_name, source_region, now):
    if dest.name:
        return dest.name
    iso8601 = "%Y%m%dT%H%M%SZ"
    return sanitize_snapshot_name(
        source_name, "copy", source_region, now.strftime(iso8601)
    )
