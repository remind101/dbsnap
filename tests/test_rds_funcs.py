import unittest

import mock

from dbsnap_verify.rds_funcs import (
    get_available_snapshots,
    get_latest_snapshot_id,
    get_database_description,
)

import boto3
rds = boto3.client("rds", region_name="us-east-1")


class TestRdsFuncs(unittest.TestCase):

    def setUp(self):
        self.snapshots = {
            "DBSnapshots": [
                {"DBSnapshotIdentifier": "rds:snapshot1",
                 "Status": "available", "SnapshotCreateTime": 1},
                {"DBSnapshotIdentifier": "rds:snapshot2",
                 "Status": "available", "SnapshotCreateTime": 2.3},
                {"DBSnapshotIdentifier": "rds:snapshot3",
                 "Status": "available", "SnapshotCreateTime": 10},
                {"DBSnapshotIdentifier": "rds:snapshot4",
                 "Status": "pending", "SnapshotCreateTime": 200},
            ]
        }
        self.db_instance_1 = {
            "DBInstances": [
                {"DBSnapshotIdentifier": "instance1",
                 "Status": "available", "InstanceCreateTime": 100},
            ]
        }
        self.db_instance_2 = {
            "DBInstances": [
                {"DBSnapshotIdentifier": "instance2",
                 "Status": "creating", "InstanceCreateTime": 100},
            ]
        }

    def test_get_available_snapshots(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.snapshots
        r = get_available_snapshots(session, "whatever")
        self.assertEqual(len(r), 3)

    def test_zero_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.snapshots
        session.describe_db_snapshots.return_value = {
            "DBSnapshots": [
                {"DBSnapshotIdentifier": "rds:snapshot4",
                 "Status": "pending", "SnapshotCreateTime": 200},
            ]
        }

        with self.assertRaises(ValueError):
            get_latest_snapshot_id(session, "my-db")

    def test_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.snapshots
        r = get_latest_snapshot_id(session, "my-db")
        self.assertEqual(r, "rds:snapshot3")

    def test_get_database_description(self):
        session = mock.MagicMock()
        session.describe_db_instances.return_value = self.db_instance_1
        r = get_database_description(session, "instance1")
        self.assertEqual(r["DBSnapshotIdentifier"], "instance1")

    def test_get_database_description_is_none(self):
        session = mock.MagicMock()
        session.exceptions.DBInstanceNotFoundFault = rds.exceptions.DBInstanceNotFoundFault
        session.describe_db_instances.side_effect = rds.exceptions.DBInstanceNotFoundFault({}, '')
        r = get_database_description(session, "instanceX")
        self.assertEqual(r, None)
