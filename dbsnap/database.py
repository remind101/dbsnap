from .utils import get_tags_for_rds_arn


class Database(object):
    """Normalise DB Instance and Cluster Descriptions into a single type."""

    def __init__(self, identifier=None, description=None, session=None):

        self.id = None
        self.description = description
        self.session = session

        if identifier:
            self.description = self.get_description_by_id(identifier)

        if self.description:
            self.setattrs_from_description()

    def __bool__(self):
        """Consider this object False if description is None."""
        if self.id is None:
            return False
        return True

    def get_description_by_id(self, identifier):
        """Return Database object or None."""
        try:
            return self.session.describe_db_instances(DBInstanceIdentifier=identifier)[
                "DBInstances"
            ][0]
        except self.session.exceptions.DBInstanceNotFoundFault:
            pass

        try:
            return self.session.describe_db_clusters(DBClusterIdentifier=identifier)[
                "DBClusters"
            ][0]
        except self.session.exceptions.DBClusterNotFoundFault:
            pass

    @property
    def tags(self):
        return get_tags_for_rds_arn(self.session, self.arn)

    @property
    def region(self):
        return self.arn.split(":")[3]

    @property
    def is_cluster(self):
        if "DBInstanceIdentifier" in self.description:
            return False
        if "DBClusterIdentifier" in self.description:
            return True
        raise LookupError(
            "invalid description: missing 'DBClusterIdentifier' or 'DBInstanceIdentifier'"
        )

    def setattrs_from_description(self):
        if self.is_cluster:
            self.compose_cluster()
        else:
            self.compose_instance()

    def _compose_common(self):
        self.kms_key_id = self.description.get("KmsKeyId")
        self.engine = self.description["Engine"]
        self.engine_version = self.description["EngineVersion"]

    def compose_instance(self):
        self._compose_common()
        self.status = self.description["DBInstanceStatus"]
        self.arn = self.description["DBInstanceArn"]
        self.id = self.description["DBInstanceIdentifier"]

    def compose_cluster(self):
        self._compose_common()
        self.status = self.description["Status"]
        self.arn = self.description["DBClusterArn"]
        self.id = self.description["DBClusterIdentifier"]
        self.cluster_member_descriptions = self.description.get("DBClusterMembers", [])
        self.cluster_member_ids = [
            m["DBInstanceIdentifier"] for m in self.cluster_member_descriptions
        ]

    @property
    def cluster_members(self):
        """Return a list of cluster member instance Database objects."""
        if self.is_cluster:
            return [
                Database(identifier=i, session=self.session)
                for i in self.cluster_member_ids
            ]

    def create_cluster_instance(
        self, instance_identifier, instance_class="db.r4.large", tags=None
    ):
        """Create an instance for this cluster."""
        if tags is None:
            tags = []
        if self.is_cluster:
            self.session.create_db_instance(
                DBInstanceIdentifier=instance_identifier,
                DBClusterIdentifier=self.id,
                Engine=self.engine,
                EngineVersion=self.engine_version,
                DBInstanceClass=instance_class,
                Tags=tags,
            )

    def delete(self):
        """Destroy the RDS instance or cluster."""
        if self.is_cluster:
            for member_id in self.cluster_member_ids:
                self.session.delete_db_instance(
                    DBInstanceIdentifier=member_id, SkipFinalSnapshot=True
                )
            self.session.delete_db_cluster(
                DBClusterIdentifier=self.id, SkipFinalSnapshot=True
            )
        else:
            self.session.delete_db_instance(
                DBInstanceIdentifier=self.id, SkipFinalSnapshot=True
            )

    def get_events(self, event_catagories=None, duration=1440):
        events = []
        if not event_catagories:
            event_catagories = []
        events.extend(
            self.session.describe_events(
                SourceIdentifier=self.id,
                SourceType="db-instance",
                EventCategories=event_catagories,
                Duration=duration,
            )["Events"]
        )
        events.extend(
            self.session.describe_events(
                SourceIdentifier=self.id,
                SourceType="db-cluster",
                EventCategories=event_catagories,
                Duration=duration,
            )["Events"]
        )
        return events

    @property
    def event_messages(self, event_catagories=None, duration=1440):
        events = self.get_events(event_catagories, duration)
        return [i["Message"] for i in events]
