from test_helper import TestHelper
from dbsnap.database import Database


class TestDatabase(TestHelper):
    def test_database_by_id(self):
        session = self._magic_rds_session()
        session.describe_db_instances.return_value = self.db_instance_desc_1
        session.describe_db_clusters.side_effect = self.rds.exceptions.DBClusterNotFoundFault(
            {}, ""
        )
        database = Database(session=session, identifier="instanceX")
        self.assertEqual(database.id, "instance1")

    def test_database_by_id_is_none(self):
        session = self._magic_rds_session()
        session.describe_db_instances.side_effect = self.rds.exceptions.DBInstanceNotFoundFault(
            {}, ""
        )
        session.describe_db_clusters.side_effect = self.rds.exceptions.DBClusterNotFoundFault(
            {}, ""
        )
        database = Database(session=session, identifier="instanceX")
        self.assertEqual(database.description, None)

    def test_database_by_description(self):
        session = self._magic_rds_session()
        database = Database(
            session=session, description=self.db_instance_desc_1["DBInstances"][0]
        )
        self.assertEqual(database.id, "instance1")

    def test_malformed_database_description(self):
        session = self._magic_rds_session()
        with self.assertRaises(LookupError):
            Database(session=session, description=self.db_instance_desc_3)
