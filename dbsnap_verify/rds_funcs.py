from operator import itemgetter

VALID_SNAPSHOT_TYPES = ["automated", "manual"]


def get_available_snapshots(session, db_id, snapshot_type=None):
    """Returns DB snapshots in the available state for a given db id.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        db_id (string): The database instance identifier whose snapshots you
            want to examine.
        snapshot_type (string): The type of snapshot to look for. One of:
            'automated', 'manual'. If not provided will return snapshots of
            both types.
    Returns:
        list: A list of dictionaries representing the resulting snapshots.
    """
    args = {'DBInstanceIdentifier': db_id}

    if snapshot_type:
        if snapshot_type not in VALID_SNAPSHOT_TYPES:
            raise ValueError("Invalid snapshot_type: %s" % snapshot_type)
        args["SnapshotType"] = snapshot_type

    r = session.describe_db_snapshots(**args)
    snapshots = r['DBSnapshots']
    snapshots.sort(key=itemgetter("SnapshotCreateTime"))
    return filter(lambda x: x["Status"] == "available", snapshots)


def get_latest_snapshot(session, db_id):
    """Returns the latest snapshot for a given database identifier.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        db_id (string): The database instance identifier whose snapshots you
            want to examine.
    Returns:
        string: The ID for the latest snapshot.
    """
    snapshots = get_available_snapshots(session, db_id, "automated")
    if not snapshots:
        raise ValueError("Unable to find any available snapshots for database "
                         "id: %s" % db_id)
    return snapshots[-1]['DBSnapshotIdentifier']


def dbsnap_verify_db_id(db_id):
    """
    Args:
        db_id (string): The database instance identifier to derive new name.
    """
    return "dbsnap-verify-{}".format(db_id)


def restore_from_latest_snapshot(session, db_id):
    """
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (string): The database instance identifier whose snapshots you
            want to examine.
    """
    latest_snapshot_id = get_latest_snapshot(session, db_id)

    new_db_id = dbsnap_verify_db_id(db_id)

    session.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_db_id,
        DBSnapshotIdentifier=latest_snapshot_id,
        PubliclyAccessible=False,
        Tags=[
            {"Key" : "Name", "Value" : new_db_id},
            {"Key" : "dbsnap-verify", "Value" : "true"},
        ],
    )


def get_database_description(session, db_id):
    """
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (string): The RDS database instance identifier.
    Returns:
        dictionary: description of RDS database instance
    """
    try:
        return session.describe_db_instances(
            DBInstanceIdentifier=db_id
        )['DBInstances'][0]
    except session.exceptions.DBInstanceNotFoundFault:
        return None

def get_database_description_for_verify(session, db_id):
    return get_database_description(session, dbsnap_verify_db_id(db_id))
