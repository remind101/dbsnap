import unittest

import mock

import json

import boto3
s3 = boto3.client("s3")

from dbsnap_verify.state_doc import get_or_create_state_doc

SNS_RDS_EVENT = {'Records': [{'EventSource': 'aws:sns', 'EventVersion': '1.0', 'EventSubscriptionArn': 'arn:aws:sns:us-west-1:12345678:test-dbsnap-verify-sns-rds-to-lambda', 'Sns': {'Type': 'Notification', 'MessageId': '9e677600-xxxx-xxxx-xxxx-251700e3b3f1', 'TopicArn': 'arn:aws:sns:us-west-1:12345678:test-dbsnap-verify-sns-rds-to-lambda', 'Subject': 'RDS Notification Message', 'Message': '{"Event Source":"db-instance","Event Time":"2018-03-05 18:22:14.893","Source ID":"dbsnap-verify-test-db-instance","Event ID":"http://docs.amazonwebservices.com/AmazonRDS/latest/UserGuide/USER_Events.html#RDS-EVENT-0043","Event Message":"Restored from snapshot rds-test-db-instance-2018-03-04-12-12-copy-us-east-1-20180304t171502z"}', 'Timestamp': '2018-03-05T18:22:36.320Z', 'MessageAttributes': {}}}]}

with open('./tests/fixtures/example_state_doc.json') as state_doc_file:
    JSON_STATE_DOC = state_doc_file.read()

mock_state_doc = mock.Mock(return_value=JSON_STATE_DOC)
mock_no_such_key_exception = mock.Mock(side_effect=s3.exceptions.NoSuchKey({}, ""))
mock_none = mock.Mock(return_value=None)


@mock.patch('dbsnap_verify.state_doc.StateDoc._save_state_doc_in_s3', mock_none)
@mock.patch('dbsnap_verify.state_doc.StateDoc._save_state_doc_in_path', mock_none)
class Tests(unittest.TestCase):

    def setUp(self):
        # mock the static json config in the Cloudwatch event rule trigger.
        # an AWS Lambda always accepts `event` as its first argument.
        self.event = {
            "database" : "test-db-instance",
            "state_doc_bucket" : "bucket-to-hold-state-documents",
            "snapshot_region" : "us-east-1",
            "database_subnet_ids": "subnet-32220000,subnet-df7d0000,subnet-b39e0000,subnet-40040000",
            "database_security_group_ids": "sg-33de0000",
        }

    @mock.patch('dbsnap_verify.state_doc.StateDoc._load_state_doc_from_s3', mock_state_doc)
    def test_get_or_create_state_doc_in_s3_doc_found_in_s3(self):
        state_doc = get_or_create_state_doc(self.event)
        self.assertEqual(state_doc.database, "test-db-instance")
        self.assertEqual(state_doc.snapshot_region, "us-east-1")
        self.assertGreater(len(state_doc.states), 5)
        self.assertEqual(state_doc.current_state, "wait")

    @mock.patch('dbsnap_verify.state_doc.StateDoc._load_state_doc_from_s3', mock_no_such_key_exception)
    def test_get_or_create_state_doc_in_s3_missing_key(self):
        """Returns a new state_doc when one is not found in s3"""
        state_doc = get_or_create_state_doc(self.event)
        self.assertEqual(state_doc.database, "test-db-instance")
        self.assertEqual(state_doc.state_doc_bucket, "bucket-to-hold-state-documents")
        self.assertEqual(state_doc.snapshot_region, "us-east-1")
        self.assertEqual(len(state_doc.states), 1)
        self.assertEqual(state_doc.current_state, "wait")

    @mock.patch('dbsnap_verify.state_doc.StateDoc._load_state_doc_from_s3', mock_state_doc)
    def test_get_or_create_state_doc_from_sns_rds_event_found(self):
        from os import environ
        environ["STATE_DOC_BUCKET"] = "bucket-to-hold-state-documents"
        state_doc = get_or_create_state_doc(SNS_RDS_EVENT)
        self.assertEqual(state_doc.database, "test-db-instance")
        self.assertEqual(state_doc.snapshot_region, "us-east-1")
        self.assertGreater(len(state_doc.states), 5)
        self.assertEqual(state_doc.current_state, "wait")

    @mock.patch('dbsnap_verify.state_doc.StateDoc._load_state_doc_from_s3', mock_no_such_key_exception)
    def test_sns_rds_event_not_found_in_s3(self):
        from os import environ
        environ["STATE_DOC_BUCKET"] = "bucket-to-hold-state-documents"
        state_doc = get_or_create_state_doc(SNS_RDS_EVENT)
        self.assertEqual(state_doc, None)
