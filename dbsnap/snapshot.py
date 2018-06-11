from .utils import get_tags_for_rds_arn


class Snapshot(object):
    """Normalise DB Instance and Cluster Snapshots into a single type."""

    def __init__(self, snapshot_description, session=None):

        self.description = snapshot_description
        self.session = session

        if self.is_cluster:
            self.compose_cluster_snapshot()
        else:
            self.compose_db_instance_snapshot()

    @property
    def is_cluster(self):
        if "DBClusterSnapshotIdentifier" in self.description:
            return True
        elif "DBSnapshotIdentifier" in self.description:
            return False
        raise LookupError(
            "invalid snapshot_description: missing 'DBClusterSnapshotIdentifier' or 'DBSnapshotIdentifier'"
        )

    @property
    def tags(self):
        return get_tags_for_rds_arn(self.session, self.arn)

    @property
    def region(self):
        return self.arn.split(":")[3]

    def _compose_common_snapshot(self):
        self.type = self.description["SnapshotType"]
        self.status = self.description["Status"]
        # only snapshots in available status have this key.
        self.created_time = self.description.get("SnapshotCreateTime")
        self.kms_key_id = self.description.get("KmsKeyId")

    def compose_cluster_snapshot(self):
        self._compose_common_snapshot()
        self.arn = self.description["DBClusterSnapshotArn"]
        self.id = self.description["DBClusterSnapshotIdentifier"]

    def compose_db_instance_snapshot(self):
        self._compose_common_snapshot()
        self.arn = self.description["DBSnapshotArn"]
        self.id = self.description["DBSnapshotIdentifier"]

    def delete(self):
        if self.is_cluster:
            self.session.delete_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot.id
            )
        else:
            self.session.delete_db_snapshot(DBSnapshotIdentifier=snapshot.id)

    def copy(self, target_snapshot_name, dest_session=None, tags=None, kms_key=None):

        if dest_session is None:
            dest_session = self.session

        copy_args = {"SourceRegion": self.region}

        if tags:
            copy_args["Tags"] = []
            for key, value in tags.items():
                copy_args["Tags"].append({"Key": key, "Value": value})

        if kms_key is not None:
            copy_args["KmsKeyId"] = kms_key

        if self.is_cluster:
            copy_args["SourceDBClusterSnapshotIdentifier"] = self.arn
            copy_args["TargetDBClusterSnapshotIdentifier"] = target_snapshot_name
            dest_session.copy_db_cluster_snapshot(**copy_args)
        else:
            copy_args["SourceDBSnapshotIdentifier"] = self.arn
            copy_args["TargetDBSnapshotIdentifier"] = target_snapshot_name
            dest_session.copy_db_snapshot(**copy_args)
