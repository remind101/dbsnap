import unittest
import datetime
from dbsnap.snapshot import Snapshot


class TestSnapshot(unittest.TestCase):
    def setUp(self):

        # example db instance snapshot_description.
        self.snapshot_description1 = {
            u"Engine": "postgres",
            u"SnapshotCreateTime": datetime.datetime(2018, 6, 2, 12, 9, 55, 276000),
            u"AvailabilityZone": "us-east-1a",
            u"DBSnapshotArn": "arn:aws:rds:us-east-1:00123456789:snapshot:rds:prod-api-db-2018-06-02-12-09",
            u"PercentProgress": 100,
            u"MasterUsername": "root",
            u"Encrypted": True,
            u"LicenseModel": "postgresql-license",
            u"StorageType": "gp2",
            u"Status": "available",
            u"VpcId": "vpc-4b6xxxxx",
            u"DBSnapshotIdentifier": "rds:prod-api-db-2018-06-02-12-09",
            u"InstanceCreateTime": datetime.datetime(2017, 4, 25, 0, 56, 56, 193000),
            u"OptionGroupName": "prod-example-com-api-masterdb-optiongroup-vrsnzezvz9y5",
            u"AllocatedStorage": 10,
            u"EngineVersion": "9.3.20",
            u"SnapshotType": "automated",
            u"KmsKeyId": "arn:aws:kms:us-east-1:00123456789:key/5582xxxx-xxxx-xxxx-93xx-xxxxxxxxxx47",
            u"IAMDatabaseAuthenticationEnabled": False,
            u"Port": 5432,
            u"DBInstanceIdentifier": "prod-api-db",
        }

        # example cluster snapshot description.
        self.snapshot_description2 = {
            u"Engine": "aurora-postgresql",
            u"SnapshotCreateTime": datetime.datetime(2018, 6, 4, 12, 11, 11, 451000),
            u"VpcId": "vpc-4b6xxxxx",
            u"DBClusterIdentifier": "prod-example-com-api-aurora-dbcluster-1dptmenxxxxxx",
            u"DBClusterSnapshotArn": "arn:aws:rds:us-east-1:00123456789:cluster-snapshot:rds:prod-example-com-api-aurora-dbcluster-1dptmenxxxxxx-2018-06-04-12-11",
            u"MasterUsername": "root",
            u"LicenseModel": "postgresql-license",
            u"Status": "available",
            u"PercentProgress": 100,
            u"DBClusterSnapshotIdentifier": "rds:prod-example-com-api-aurora-dbcluster-1dptmenxxxxxx-2018-06-04-12-11",
            u"KmsKeyId": "arn:aws:kms:us-east-1:00123456789:key/5582xxxx-xxxx-xxxx-93xx-xxxxxxxxxx47",
            u"ClusterCreateTime": datetime.datetime(2018, 5, 26, 3, 27, 10, 953000),
            u"StorageEncrypted": True,
            u"AllocatedStorage": 1,
            u"EngineVersion": "9.6.6",
            u"SnapshotType": "automated",
            u"AvailabilityZones": ["us-east-1a", "us-east-1b", "us-east-1c"],
            u"IAMDatabaseAuthenticationEnabled": False,
            u"Port": 0,
        }

        # example malformed snapshot description.
        self.snapshot_description3 = {"bad": "data"}

    def test_db_instance_snapshot(self):
        snapshot = Snapshot(self.snapshot_description1)
        self.assertEquals(snapshot.arn, self.snapshot_description1["DBSnapshotArn"])
        self.assertEquals(
            snapshot.id, self.snapshot_description1["DBSnapshotIdentifier"]
        )
        self.assertEquals(snapshot.region, "us-east-1")

    def test_cluster_snapshot(self):
        snapshot = Snapshot(self.snapshot_description2)
        self.assertEquals(
            snapshot.arn, self.snapshot_description2["DBClusterSnapshotArn"]
        )
        self.assertEquals(
            snapshot.id, self.snapshot_description2["DBClusterSnapshotIdentifier"]
        )
        self.assertEquals(snapshot.region, "us-east-1")

    def test_malformed_snapshot_description(self):
        with self.assertRaises(LookupError):
            Snapshot(self.snapshot_description3)
