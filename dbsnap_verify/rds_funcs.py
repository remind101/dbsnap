from operator import itemgetter

import boto3
rds = boto3.client("rds")

def get_database_description(db_instance_identifier):
    descriptions = rds.describe_db_instances(
        DBInstanceIdentifier=db_instance_identifier
    )['DBInstances']
    if len(descriptions) == 1:
        return descriptions[0]
    elif len(descriptions) > 1:
        raise Exception(
            "DBInstanceIdentifier ({}) matches multiple instances".format(
                db_instance_identifier
            )
        )

def get_snapshot_descriptions(db_instance_identifier):
    descriptions = rds.describe_db_snapshots(
        DBInstanceIdentifier=db_instance_identifier
    )['DBSnapshots']
    descriptions.sort(key=itemgetter("SnapshotCreateTime"))
    return descriptions

def restore_from_latest_snapshot(db_instance_identifier):
    latest_snapshot_desc = get_snapshot_descriptions(db_instance_identifier)[-1]

    new_db_instance_identifier = "dbsnap-verify-{}".format(db_instance_identifier)

    rds.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_db_instance_identifier,
        DBSnapshotIdentifier=latest_snapshot_desc["DBSnapshotIdentifier"],
        PubliclyAccessible=False,
        Tags=[
            {"Key" : "Name", "Value" : new_db_instance_identifier}
            {"Key" : "dbsnap-verify", "Value" : "true"}
        ],
    )
