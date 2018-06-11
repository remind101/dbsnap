from operator import attrgetter

from random import choice

from string import digits

try:
    from string import letters
except ImportError:
    from string import ascii_letters as letters

from .snapshot import Snapshot


VALID_SNAPSHOT_TYPES = ["automated", "manual"]

SAFETY_TAG_KEY = "dbsnap-verify"
SAFETY_TAG_VAL = "true"


def get_rds_type(session, identifier):
    try:
        session.describe_db_instances(DBInstanceIdentifier=identifier)["DBInstances"]
        return "db"
    except session.exceptions.DBInstanceNotFoundFault:
        pass
    try:
        session.describe_db_clusters(DBClusterIdentifier=identifier)["DBClusters"]
        return "cluster"
    except session.exceptions.DBClusterNotFoundFault:
        pass
    raise LookupError(
        "No RDS DB or Cluster found with identifier: {}".format(identifier)
    )


def get_available_snapshots(session, identifier, snapshot_type=None):
    """Returns snapshots in the available state for a given DB or Cluster `identifier`.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        identifier (str): The database instance or cluster identifier whose snapshots
            you would like to examine.
        snapshot_type (str): The type of snapshot to look for. One of:
            'automated', 'manual'. If not provided will return snapshots of
            both types.
    Returns:
        list: A list of dbsnap.Snapshot objects.
    """
    if get_rds_type(session, identifier) == "db":
        args = {"DBInstanceIdentifier": identifier}
        snapshots = session.describe_db_snapshots(**args)["DBSnapshots"]
    else:
        args = {"DBClusterIdentifier": identifier}
        snapshots = session.describe_db_cluster_snapshots(**args)["DBClusterSnapshots"]

    if snapshot_type:
        if snapshot_type not in VALID_SNAPSHOT_TYPES:
            raise ValueError("Invalid snapshot_type: %s" % snapshot_type)
        args["SnapshotType"] = snapshot_type

    # convert snapshot descriptions into normalized Snapshot objects.
    snapshots = [Snapshot(snapshot, session) for snapshot in snapshots]

    # filter first because only available snapshots have a SnapshotCreateTime.
    snapshots = [snapshot for snapshot in snapshots if snapshot.status == "available"]

    # sort snapshots list of Snapshots by created_time.
    snapshots.sort(key=attrgetter("created_time"))

    return snapshots


def get_available_dbsnap_snapshots(session, identifier):
    """Returns DB snapshots in the available state for a given db id.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        identifier (str): The database instance or cluster identifier whose snapshots
            you would like to examine.
    Returns:
        list: A list of dictionaries representing the resulting snapshots.
    """
    dbsnap_snapshots = []
    snapshots = get_available_snapshots(session, identifier, snapshot_type="manual")
    for snapshot in snapshots:
        if snapshot.tags.get("created_by") == "dbsnap-copy":
            dbsnap_snapshots.append(snapshot)
    return dbsnap_snapshots


def get_old_dbsnap_snapshots(session, identifier, keep_count):
    """Returns the latest snapshots for a given database identifier.

    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        identifier (str): The database instance identifier whose snapshots you
            want to examine.
        keep_count(int): The # of most recent snapshots to ignore.

    Returns:
        list: A list of old snapshot IDs.
    """
    snapshots = get_available_dbsnap_snapshots(session, identifier)
    trim_index = len(snapshots) - keep_count
    # trim off the keepers from the list of old snapshots.
    return snapshots[:trim_index]


def get_latest_snapshot(session, identifier, snapshot_type=None):
    """Returns the latest snapshot for a given database identifier.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        identifier (str): The database instance or cluster identifier whose snapshots
            you would like to examine.
    Returns:
        dict: The snapshot description document for the latest snapshot.
    """
    snapshots = get_available_snapshots(session, identifier, snapshot_type)
    if not snapshots:
        raise ValueError(
            "No available snapshots for database id: {}".format(identifier)
        )
    return snapshots[-1]


def generate_password(size=9, pool=letters + digits):
    """Return a system generated password.
    Args:
        size (int): The desired length of the password to generate (Default 9).
        pool (list): list of chars to choose from.
            (Default digits and letters [upper/lower])
    Returns:
        str: the raw password
    """
    return "".join([choice(pool) for i in range(size)])


def dbsnap_verify_identifier(identifier):
    """
    Args:
        identifier (str): The database instance identifier to derive new name.
    """
    return "dbsnap-verify-{}".format(identifier)


def get_database_subnet_group_description(session, identifier):
    """
    Returns database subnet_group description document or None.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance identifier.
    Returns:
        dictionary: description of RDS database instance
    """
    try:
        return session.describe_db_subnet_groups(DBSubnetGroupName=identifier)[
            "DBSubnetGroups"
        ][0]
    except session.exceptions.DBSubnetGroupNotFoundFault:
        return None


def safer_create_database_subnet_group(session, identifier, sn_ids):
    new_identifier = dbsnap_verify_identifier(identifier)

    if get_database_subnet_group_description(session, new_identifier):
        destroy_database_subnet_group(session, new_identifier)

    session.create_db_subnet_group(
        DBSubnetGroupName=new_identifier,
        DBSubnetGroupDescription=new_identifier,
        SubnetIds=sn_ids,
        Tags=[
            {"Key": "Name", "Value": new_identifier},
            {"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL},
        ],
    )


def restore_from_latest_snapshot(session, identifier, sn_ids):
    """Restores a temp db instance from the latest snapshot.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The database instance identifier whose snapshots you
            want to examine.
    """
    latest_snapshot_id = get_latest_snapshot_id(session, identifier)

    safer_create_database_subnet_group(session, identifier, sn_ids)

    new_identifier = dbsnap_verify_identifier(identifier)
    session.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_identifier,
        DBSubnetGroupName=new_identifier,
        DBSnapshotIdentifier=latest_snapshot_id,
        PubliclyAccessible=False,
        MultiAZ=False,
        Tags=[
            {"Key": "Name", "Value": new_identifier},
            {"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL},
        ],
    )


def get_database_description(session, identifier):
    """
    Returns database description document or None.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance identifier.
    Returns:
        dictionary: description of RDS database instance
    """
    try:
        return session.describe_db_instances(DBInstanceIdentifier=identifier)[
            "DBInstances"
        ][0]
    except session.exceptions.DBInstanceNotFoundFault:
        return None


def get_database_events(session, identifier, event_catagories=None, duration=1440):
    if not event_catagories:
        event_catagories = []
    return session.describe_events(
        SourceIdentifier=identifier,
        SourceType="db-instance",
        EventCategories=event_catagories,
        Duration=duration,
    )["Events"]


def rds_event_messages(session, identifier, event_catagories=None, duration=1440):
    events = get_database_events(session, identifier, event_catagories, duration)
    return [i["Message"] for i in events]


def modify_db_instance_for_verify(session, identifier, sg_ids):
    """Modify RDS DB Instance to allow connections.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance identifier to reset.
    Returns:
        str: new raw password
    """
    # 16 chars was an arbitrary choice.
    new_password = generate_password(16)
    session.modify_db_instance(
        ApplyImmediately=True,
        DBInstanceIdentifier=identifier,
        VpcSecurityGroupIds=sg_ids,
        BackupRetentionPeriod=0,
        MasterUserPassword=new_password,
    )
    return new_password


def make_tag_dict(tag_list):
    """Returns a dictionary of existing tags.
    Args:
        tag_list (list): a list of tag dicts.
    Returns:
        dict: A dictionary where tag names are keys and tag values are values.
    """
    return {i["Key"]: i["Value"] for i in tag_list}


def get_tags_for_rds_arn(session, rds_arn):
    """Returns a dictionary of existing tags.
    Args:
        rds_arn (str): an RDS resource ARN.
    Returns:
        dict: A dictionary where tag names are keys and tag values are values.
    """
    return make_tag_dict(
        session.list_tags_for_resource(ResourceName=rds_arn)["TagList"]
    )


def destroy_database(session, identifier, db_arn=None):
    """Destroy the RDS db instance.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance identifier to destroy.
    """
    if db_arn is None:
        description = get_database_description(session, identifier)
        db_arn = description["DBInstanceArn"]

    tags = get_tags_for_rds_arn(session, db_arn)

    if tags.get(SAFETY_TAG_KEY) != SAFETY_TAG_VAL:
        raise Exception(
            "sheepishly refusing to destroy {}, missing `{}` tag".format(
                identifier, SAFETY_TAG_KEY
            )
        )

    session.delete_db_instance(DBInstanceIdentifier=identifier, SkipFinalSnapshot=True)


def destroy_database_subnet_group(session, identifier):
    """Destroy the RDS db instance subnet group.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance subnet identifier to destroy.
    """
    if get_database_subnet_group_description(session, identifier) is not None:
        session.delete_db_subnet_group(DBSubnetGroupName=identifier)
