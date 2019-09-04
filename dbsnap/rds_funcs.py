from operator import attrgetter

from random import choice

from string import digits

try:
    from string import letters
except ImportError:
    from string import ascii_letters as letters

from .snapshot import Snapshot
from .database import Database

VALID_SNAPSHOT_TYPES = ["automated", "manual"]

SAFETY_TAG_KEY = "dbsnap-verify"
SAFETY_TAG_VAL = "true"


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
    args = {}

    if snapshot_type:
        if snapshot_type not in VALID_SNAPSHOT_TYPES:
            raise ValueError("Invalid snapshot_type: {}".format(snapshot_type))
        args["SnapshotType"] = snapshot_type

    # assume identifier is for a regular RDS database.
    snapshots = session.describe_db_snapshots(DBInstanceIdentifier=identifier, **args)[
        "DBSnapshots"
    ]

    if not snapshots:
        # assume identifier is for a cluster RDS database.
        snapshots = session.describe_db_cluster_snapshots(
            DBClusterIdentifier=identifier, **args
        )["DBClusterSnapshots"]

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
            "No available snapshots found for identifier: {}".format(identifier)
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
    new_identifier = "dbsv-{}".format(identifier)
    if len(new_identifier) > 63:
        # then generated identifier for the restore much be between 1-63 charecters.
        # so we truncate new_identifier to 60 charecters.
        new_identifier = new_identifier[:60]
    return new_identifier


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
    snapshot = get_latest_snapshot(session, identifier)

    safer_create_database_subnet_group(session, identifier, sn_ids)

    new_identifier = dbsnap_verify_identifier(identifier)

    if snapshot.is_cluster:
        session.restore_db_cluster_from_snapshot(
            DBClusterIdentifier=new_identifier,
            DBSubnetGroupName=new_identifier,
            SnapshotIdentifier=snapshot.id,
            Engine=snapshot.engine,
            EngineVersion=snapshot.engine_version,
            Tags=[
                {"Key": "Name", "Value": new_identifier},
                {"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL},
            ],
        )

    else:
        session.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=new_identifier,
            DBSubnetGroupName=new_identifier,
            DBSnapshotIdentifier=snapshot.id,
            PubliclyAccessible=False,
            MultiAZ=False,
            Tags=[
                {"Key": "Name", "Value": new_identifier},
                {"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL},
            ],
        )


def create_cluster_instance(cluster, instance_identifier):
    # No straight forward way to use the same instance class as
    # the source cluster (Aurora) but not sure it matters.
    # Hardcoding this instance_class, currently the smallest/cheapest.
    cluster.create_cluster_instance(
        instance_identifier,
        "db.r4.large",
        tags=[
            {"Key": "Name", "Value": instance_identifier},
            {"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL},
        ],
    )


def modify_instance_or_cluster_for_verify(database, sg_ids):
    """Modify an RDS Instance or Cluster to allow connections.
    Args:
        database (:class:`dbsnap.database.Database`): the database or cluster
            to modify to allow access for verification routines.
        sg_ids (list): Security group ids to add to instance or cluster.
    Returns:
        str: new raw password
    """
    # 16 chars was an arbitrary choice.
    new_password = generate_password(16)

    if database.is_cluster:
        database.session.modify_db_cluster(
            ApplyImmediately=True,
            DBClusterIdentifier=database.id,
            VpcSecurityGroupIds=sg_ids,
            BackupRetentionPeriod=1,
            PreferredMaintenanceWindow="Sun:18:00-Sun:23:59",
            MasterUserPassword=new_password,
        )
    else:
        database.session.modify_db_instance(
            ApplyImmediately=True,
            DBInstanceIdentifier=database.id,
            VpcSecurityGroupIds=sg_ids,
            BackupRetentionPeriod=0,
            MasterUserPassword=new_password,
        )
    return new_password


def delete_verified_database(database):
    """Given a dbsnap.database.Database object, delete if properly tagged."""
    if database.tags.get(SAFETY_TAG_KEY) != SAFETY_TAG_VAL:
        raise Exception(
            "sheepishly refusing to destroy {}, missing `{}` tag".format(
                database.id, SAFETY_TAG_KEY
            )
        )
    database.delete()


def destroy_database_subnet_group(session, identifier):
    """Destroy the RDS db instance subnet group.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        identifier (str): The RDS database instance subnet identifier to destroy.
    """
    try:
        session.delete_db_subnet_group(DBSubnetGroupName=identifier)
    except session.exceptions.DBSubnetGroupNotFoundFault:
        # if it doesn't exist, there is nothing to delete.
        pass
