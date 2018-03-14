import unittest

from dbsnap_verify.datadog_output import (
    datadog_lambda_check_output,
    datadog_lambda_metric_output,
)

class Tests(unittest.TestCase):

    def test_datadog_check_ok(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="OK",
            metric_tags={"database" : "test-db-instance"}
        )
        self.assertIn("|#database:test-db-instance", output)
        self.assertIn("MONITORING|", output)
        self.assertIn("|0|", output)

    def test_datadog_check_critical(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="CRITICAL",
            metric_tags={"database" : "test-db-instance"}
        )
        self.assertIn("|#database:test-db-instance", output)
        self.assertIn("MONITORING|", output)
        self.assertIn("|2|", output)

    def test_datadog_check_multi_tags(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="OK",
            metric_tags={"database" : "test-db-instance", "another" : 3}
        )
        self.assertIn("|#database:test-db-instance,another:3", output)

    def test_datadog_check_string_tag(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="CRITICAL",
            metric_tags="database:test-db-instance"
        )
        self.assertIn("|#database:test-db-instance", output)

    def test_datadog_check_string_tag2(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="CRITICAL",
            metric_tags="#database:test-db-instance"
        )
        self.assertIn("|#database:test-db-instance", output)

    def test_datadog_check_list_tags(self):
        output = datadog_lambda_check_output(
            metric_name="dbsnap-verify.lambda",
            metric_value="CRITICAL",
            metric_tags=["database:test-db-instance", "another"]
        )
        self.assertIn("|#database:test-db-instance,another", output)

    def test_datadog_output_invalid_metric_type(self):
        with self.assertRaises(Exception):
            datadog_lambda_metric_output(
                metric_name="dbsnap-verify.lambda",
                metric_type="taco",
                metric_value=42,
                metric_tags=["database:test-db-instance", "another"]
            )
