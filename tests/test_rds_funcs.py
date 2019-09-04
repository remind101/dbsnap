from test_helper import TestHelper

from dbsnap.rds_funcs import (
    get_available_snapshots,
    get_available_dbsnap_snapshots,
    get_old_dbsnap_snapshots,
    get_latest_snapshot,
    dbsnap_verify_identifier,
    delete_verified_database,
    SAFETY_TAG_KEY,
    SAFETY_TAG_VAL,
)

import mock

from dbsnap.database import Database


class TestRdsFuncs(TestHelper):

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
                    "SnapshotType": "automatic",
                    "DBSnapshotArn": "arn:1",
                    "Engine": "postgres",
                    "EngineVersion": "9.6.6",
                }
            ]
        }

        with self.assertRaises(ValueError):
            get_latest_snapshot(session, "my-db")

    def test_get_latest_snapshot(self):
        session = mock.MagicMock()
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc
        r = get_latest_snapshot(session, "my-db")
        self.assertEqual(r.id, "rds:snapshot3")

    def test_delete_verified_database_missing_safety_tag(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList": [{"Key": "irrelevant", "Value": "1"}]
        }
        database = Database(
            session=session, description=self.db_instance_desc_1["DBInstances"][0]
        )
        database.session = session
        with self.assertRaises(Exception):
            delete_verified_database(database)

    def test_delete_verified_database_incorrect_safety_tag_value(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList": [{"Key": SAFETY_TAG_KEY, "Value": "1"}]
        }
        database = Database(
            session=session, description=self.db_instance_desc_1["DBInstances"][0]
        )
        database.session = session
        with self.assertRaises(Exception):
            delete_verified_database(database)

    def test_delete_verified_database(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.return_value = {
            "TagList": [{"Key": SAFETY_TAG_KEY, "Value": SAFETY_TAG_VAL}]
        }
        database = Database(
            session=session, description=self.db_instance_desc_1["DBInstances"][0]
        )
        database.session = session
        delete_verified_database(database)

    def test_get_available_dbsnap_snapshots(self):
        session = mock.MagicMock()
        session.list_tags_for_resource.side_effect = self.fake_list_tags
        session.describe_db_snapshots.return_value = self.fake_snapshot_desc
        r = get_available_dbsnap_snapshots(session, "whatever")
        self.assertEqual(len(r), 4)

    def test_get_old_dbsnap_snapshots(self):
        # session, db_id, keep_count)
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

    def test_dbsnap_verify_identifier(self):

        db_id = "test-acmein"
        new_identifier = dbsnap_verify_identifier(db_id)
        self.assertTrue(new_identifier.startswith("dbsv-"))
        self.assertEqual(new_identifier, "dbsv-test-acmein")

        # test truncated case.
        db_id = "test-acmein-com-pg-aurora-multitenant-dbcluster-146qo1hzclehn"
        new_identifier = dbsnap_verify_identifier(db_id)
        self.assertEqual(new_identifier, "dbsv-test-acmein-com-pg-aurora-multitenant-dbcluster-146qo1h")
