import unittest
import mock
import boto3


class TestHelper(unittest.TestCase):
    def _magic_rds_session(self):
        session = mock.MagicMock()
        session.exceptions.DBInstanceNotFoundFault = (
            self.rds.exceptions.DBInstanceNotFoundFault
        )
        session.exceptions.DBClusterNotFoundFault = (
            self.rds.exceptions.DBClusterNotFoundFault
        )
        return session

    def setUp(self):
        self.rds = boto3.client("rds", region_name="us-east-1")
        self.fake_snapshot_desc = {
            "DBSnapshots": [
                {
                    "DBSnapshotIdentifier": "rds:snapshot1",
                    "DBSnapshotArn": "arn:1",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "available",
                    "SnapshotType": "manual",
                    "SnapshotCreateTime": 1,
                },
                {
                    "DBSnapshotIdentifier": "rds:snapshot2",
                    "DBSnapshotArn": "arn:2",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "available",
                    "SnapshotType": "manual",
                    "SnapshotCreateTime": 2.3,
                },
                {
                    "DBSnapshotIdentifier": "rds:snapshot3",
                    "DBSnapshotArn": "arn:3",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "available",
                    "SnapshotType": "manual",
                    "SnapshotCreateTime": 10,
                },
                # Note: only available snapshots have a SnapshotCreateTime.
                {
                    "DBSnapshotIdentifier": "rds:snapshot4",
                    "DBSnapshotArn": "arn:4",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "pending",
                    "SnapshotType": "manual",
                },
                {
                    "DBSnapshotIdentifier": "rds:snapshot5",
                    "DBSnapshotArn": "arn:5",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "available",
                    "SnapshotType": "manual",
                    "SnapshotCreateTime": 8,
                },
                {
                    "DBSnapshotIdentifier": "rds:snapshot6",
                    "DBSnapshotArn": "arn:6",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                    "Status": "available",
                    "SnapshotType": "manual",
                    "SnapshotCreateTime": 9,
                },
            ]
        }
        self.db_instance_desc_1 = {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "instance1",
                    "DBInstanceStatus": "available",
                    "DBInstanceArn": "arn:1234",
                    "InstanceCreateTime": 100,
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                }
            ]
        }
        self.db_instance_desc_2 = {
            "DBInstances": [
                {
                    "DBClusterIdentifier": "instance2",
                    "DBClusterArn": "arn:1234",
                    "Status": "creating",
                    "InstanceCreateTime": 100,
                    "Engine": "aurora-postgres",
                    "EngineVersion": "9.6.6",
                }
            ]
        }
        # example malformed database description.
        self.db_instance_desc_3 = {"bad": "data"}

        self.fake_tags = {
            "arn:1": {"TagList": [{"Key": "created_by", "Value": "dbsnap-copy"}]},
            "arn:2": {"TagList": [{"Key": "created_by", "Value": "dbsnap-copy"}]},
            "arn:3": {"TagList": [{"Key": "created_by", "Value": "dbsnap-copy"}]},
            "arn:4": {"TagList": [{"Key": "created_by", "Value": "dbsnap-copy"}]},
            "arn:5": {"TagList": [{"Key": "created_by", "Value": "dbsnap-copy"}]},
            "arn:6": {"TagList": [{"Key": "created_by", "Value": "not-dbsnap-copy"}]},
            "arn:7": {"TagList": []},
        }

        def fake_list_tags_for_resource(ResourceName):
            return self.fake_tags[ResourceName]

        self.fake_list_tags = fake_list_tags_for_resource

