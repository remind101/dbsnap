from operator import itemgetter

from random import choice

from string import digits

try:
    from string import letters
except ImportError:
    from string import ascii_letters as letters

VALID_SNAPSHOT_TYPES = ["automated", "manual"]

SAFETY_TAG_KEY = "dbsnap-verify"
SAFETY_TAG_VAL = "true"


def generate_password(size=9, pool=letters+digits):
    """Return a system generated password.
    Args:
        size (int): The desired length of the password to generate (Default 9).
        pool (list): list of chars to choose from.
            (Default digits and letters [upper/lower])
    Returns:
        str: the raw password
    """
    return ''.join([choice(pool) for i in range(size)])


def get_available_snapshots(session, db_id, snapshot_type=None):
    """Returns DB snapshots in the available state for a given db id.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        db_id (str): The database instance identifier whose snapshots you
            want to examine.
        snapshot_type (str): The type of snapshot to look for. One of:
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
    return list(filter(lambda x: x["Status"] == "available", snapshots))


def get_latest_snapshot(session, db_id, snapshot_type=None):
    """Returns the latest snapshot for a given database identifier.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        db_id (str): The database instance identifier whose snapshots you
            want to examine.
    Returns:
        dict: The snapshot description document for the latest snapshot.
    """
    snapshots = get_available_snapshots(session, db_id, snapshot_type)
    if not snapshots:
        raise ValueError("Unable to find any available snapshots for database "
                         "id: %s" % db_id)
    return snapshots[-1]


def get_latest_snapshot_id(session, db_id, snapshot_type=None):
    """Returns the latest snapshot for a given database identifier.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api connection
            where the database is located.
        db_id (str): The database instance identifier whose snapshots you
            want to examine.
    Returns:
        str: The ID for the latest snapshot.
    """
    return get_latest_snapshot(
        session, db_id, snapshot_type
    )['DBSnapshotIdentifier']


def dbsnap_verify_db_id(db_id):
    """
    Args:
        db_id (str): The database instance identifier to derive new name.
    """
    return "dbsnap-verify-{}".format(db_id)


def get_database_subnet_group_description(session, db_id):
    """
    Returns database subnet_group description document or None.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The RDS database instance identifier.
    Returns:
        dictionary: description of RDS database instance
    """
    try:
        return session.describe_db_subnet_groups(
            DBSubnetGroupName=db_id
        )['DBSubnetGroups'][0]
    except session.exceptions.DBSubnetGroupNotFoundFault:
        return None


def safer_create_database_subnet_group(session, db_id, sn_ids):
    new_db_id = dbsnap_verify_db_id(db_id)
    
    if get_database_subnet_group_description(session, new_db_id):
        destroy_database_subnet_group(session, new_db_id)

    session.create_db_subnet_group(
        DBSubnetGroupName = new_db_id,
        DBSubnetGroupDescription = new_db_id,
        SubnetIds = sn_ids,
        Tags=[
            {"Key" : "Name", "Value" : new_db_id},
            {"Key" : SAFETY_TAG_KEY, "Value" : SAFETY_TAG_VAL},
        ],
    )


def restore_from_latest_snapshot(session, db_id, sn_ids):
    """Restores a temp db instance from the latest snapshot.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The database instance identifier whose snapshots you
            want to examine.
    """
    latest_snapshot_id = get_latest_snapshot_id(session, db_id)

    safer_create_database_subnet_group(session, db_id, sn_ids)

    new_db_id = dbsnap_verify_db_id(db_id)
    session.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_db_id,
        DBSubnetGroupName=new_db_id,
        DBSnapshotIdentifier=latest_snapshot_id,
        PubliclyAccessible=False,
        MultiAZ=False,
        Tags=[
            {"Key" : "Name", "Value" : new_db_id},
            {"Key" : SAFETY_TAG_KEY, "Value" : SAFETY_TAG_VAL},
        ],
    )


def get_database_description(session, db_id):
    """
    Returns database description document or None.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The RDS database instance identifier.
    Returns:
        dictionary: description of RDS database instance
    """
    try:
        return session.describe_db_instances(
            DBInstanceIdentifier=db_id
        )['DBInstances'][0]
    except session.exceptions.DBInstanceNotFoundFault:
        return None


def get_database_events(session, db_id, event_catagories=None, duration=1440):
    if not event_catagories:
        event_catagories = []
    return session.describe_events(
        SourceIdentifier=db_id,
        SourceType='db-instance',
        EventCategories = event_catagories,
        Duration = duration,
    )['Events']


def rds_event_messages(session, db_id, event_catagories=None, duration=1440):
    events = get_database_events(session, db_id, event_catagories, duration)
    return [i['Message'] for i in events]


def modify_db_instance_for_verify(session, db_id, sg_ids):
    """Modify RDS DB Instance to allow connections.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The RDS database instance identifier to reset.
    Returns:
        str: new raw password
    """
    # 16 chars was an arbitrary choice.
    new_password = generate_password(16)
    session.modify_db_instance(
        ApplyImmediately=True,
        DBInstanceIdentifier=db_id,
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


def destroy_database(session, db_id, db_arn=None):
    """Destroy the RDS db instance.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The RDS database instance identifier to destroy.
    """
    if db_arn is None:
        description = get_database_description(session, db_id)
        db_arn = description["DBInstanceArn"]

    tags = get_tags_for_rds_arn(session, db_arn)

    if tags.get(SAFETY_TAG_KEY, "false") != SAFETY_TAG_VAL:
        raise Exception(
            "sheepishly refusing to destroy {}, missing `{}` tag".format(
                db_id,
                SAFETY_TAG_KEY
            )
        )

    session.delete_db_instance(
        DBInstanceIdentifier=db_id,
        SkipFinalSnapshot=True
    )


def destroy_database_subnet_group(session, db_id):
    """Destroy the RDS db instance subnet group.
    Args:
        session (:class:`boto.rds2.layer1.RDSConnection`): The RDS api
            connection where the database is located.
        db_id (str): The RDS database instance subnet identifier to destroy.
    """
    if get_database_subnet_group_description(session, db_id) is not None:
        session.delete_db_subnet_group(
            DBSubnetGroupName=db_id,
        )


