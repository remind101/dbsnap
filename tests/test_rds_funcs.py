import unittest

import mock

from dbsnap_verify.rds_funcs import (
    get_available_snapshots,
    get_latest_snapshot,
)

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
        self.db_instances = {
            "DBInstances": [
                {"DBInstanceIdentifier": "rds:instance1",
                 "Status": "available", "InstanceCreateTime": 1},
                {"DBSnapshotIdentifier": "rds:instance2",
                 "Status": "available", "InstanceCreateTime": 2.3},
                {"DBSnapshotIdentifier": "rds:instance3",
                 "Status": "available", "InstanceCreateTime": 10},
                {"DBSnapshotIdentifier": "rds:instance4",
                 "Status": "creating", "InstanceCreateTime": 200},
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
            get_latest_snapshot(session, "my-db")

    def test_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.snapshots
        r = get_latest_snapshot(session, "my-db")
        self.assertEqual(r, "rds:snapshot3")

    def test_get_database_description(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.snapshots
        r = get_latest_snapshot(session, "my-db")
        self.assertEqual(r, "rds:snapshot3")
