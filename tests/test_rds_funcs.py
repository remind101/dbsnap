import unittest

import mock

from dbsnap.rds_funcs import (
    get_available_snapshots,
    get_available_dbsnap_snapshots,
    get_old_dbsnap_snapshots,
    get_latest_snapshot,
    get_database_description,
    destroy_database,
    SAFETY_TAG_KEY,
    SAFETY_TAG_VAL,
)

import boto3
rds = boto3.client("rds", region_name="us-east-1")


class TestRdsFuncs(unittest.TestCase):

    def setUp(self):
        self.fake_snapshot_desc = {
            "DBSnapshots": [
                {"DBSnapshotIdentifier": "rds:snapshot1",
                 "DBSnapshotArn" : "arn:1",
                 "Status": "available",
                 "SnapshotType" : "manual",
                 "SnapshotCreateTime": 1},
                {"DBSnapshotIdentifier": "rds:snapshot2",
                 "DBSnapshotArn" : "arn:2",
                 "Status": "available",
                 "SnapshotType" : "manual",
                 "SnapshotCreateTime": 2.3},
                {"DBSnapshotIdentifier": "rds:snapshot3",
                 "DBSnapshotArn" : "arn:3",
                 "Status": "available",
                 "SnapshotType" : "manual",
                 "SnapshotCreateTime": 10},
                # Note: only available snapshots have a SnapshotCreateTime.
                {"DBSnapshotIdentifier": "rds:snapshot4",
                 "DBSnapshotArn" : "arn:4",
                 "Status": "pending",
                 "SnapshotType" : "manual",
                },
                {"DBSnapshotIdentifier": "rds:snapshot5",
                 "DBSnapshotArn" : "arn:5",
                 "SnapshotType" : "manual",
                 "Status": "available",
                 "SnapshotCreateTime": 8},
                {"DBSnapshotIdentifier": "rds:snapshot6",
                 "DBSnapshotArn" : "arn:6",
                 "SnapshotType" : "manual",
                 "Status": "available",
                 "SnapshotCreateTime": 9},
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
        self.fake_tags = {
            "arn:1" : {
                "TagList": [{"Key" : "created_by", "Value": "dbsnap-copy"}]
            },
            "arn:2" : {
                "TagList": [{"Key" : "created_by", "Value": "dbsnap-copy"}]
            },
            "arn:3" : {
                "TagList": [{"Key" : "created_by", "Value": "dbsnap-copy"}]
            },
            "arn:4" : {
                "TagList": [{"Key" : "created_by", "Value": "dbsnap-copy"}]
            },
            "arn:5" : {
                "TagList": [{"Key" : "created_by", "Value": "dbsnap-copy"}]
            },
            "arn:6" : {
                "TagList": [{"Key" : "created_by", "Value": "not-dbsnap-copy"}]
            },
            "arn:7" : {"TagList": []},
        }

        def fake_list_tags_for_resource(ResourceName):
            return self.fake_tags[ResourceName]

        self.fake_list_tags = fake_list_tags_for_resource

    def test_get_available_snapshots(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc 
        r = get_available_snapshots(session, "whatever")
        self.assertEqual(len(r), 5)

    def test_zero_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = {
            "DBSnapshots": [
                {
                    "DBSnapshotIdentifier": "rds:snapshot4",
                    "Status": "pending",
                    "SnapshotCreateTime": 200,
                    "SnapshotType" : "automatic",
                    "DBSnapshotArn" : "arn:1"
                },
            ]
        }

        with self.assertRaises(ValueError):
            get_latest_snapshot(session, "my-db")

    def test_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc
        r = get_latest_snapshot(session, "my-db")
        self.assertEqual(r.id, "rds:snapshot3")

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

    def test_destroy_database_missing_safety_tag(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList" : [
                { "Key" : "irrelevant", "Value" : "1" }
            ]
        }
        with self.assertRaises(Exception):
            r = destroy_database(
                session, identifier="my-db" , db_arn="arn:rds:1234"
            )

    def test_destroy_database_incorrect_safety_tag_value(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList" : [
                { "Key" : SAFETY_TAG_KEY, "Value" : "1" }
            ]
        }
        with self.assertRaises(Exception):
            r = destroy_database(
                session, identifier="my-db" , db_arn="arn:rds:1234"
            )

    def test_destroy_database(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList" : [
                { "Key" : SAFETY_TAG_KEY, "Value" : SAFETY_TAG_VAL }
            ]
        }
        r = destroy_database(
            session, identifier="my-db" , db_arn="arn:rds:1234"
        )

    def test_get_available_dbsnap_snapshots(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.side_effect = self.fake_list_tags
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc
        r = get_available_dbsnap_snapshots(session, "whatever")
        self.assertEqual(len(r), 4)

    def test_get_old_dbsnap_snapshots(self):
        #session, db_id, keep_count)
        session = mock.MagicMock()
        session.list_tags_for_resource.side_effect = self.fake_list_tags
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc

        r = get_old_dbsnap_snapshots(session, "whatever", keep_count=2)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].id, "rds:snapshot1")
        self.assertEqual(r[1].id, "rds:snapshot2")

        # make sure snapshots are tagged with `created_by: dbsnap-copy`
        self.assertEqual(r[0].tags["created_by"], "dbsnap-copy")
        self.assertEqual(r[1].tags["created_by"], "dbsnap-copy")

        r = get_old_dbsnap_snapshots(session, "whatever", keep_count=3)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].id, "rds:snapshot1")

        r = get_old_dbsnap_snapshots(session, "whatever", keep_count=0)
        self.assertEqual(len(r), 4)
        self.assertEqual(r[0].id, "rds:snapshot1")
        self.assertEqual(r[1].id, "rds:snapshot2")
        self.assertEqual(r[2].id, "rds:snapshot5")
        self.assertEqual(r[3].id, "rds:snapshot3")
