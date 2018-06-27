import unittest
from collections import namedtuple
from datetime import datetime

import mock

from dbsnap_copy import (
    Source,
    Dest,
    parse_source,
    parse_destination,
    sanitize_snapshot_name,
    get_snapshot_target_name,
)


class TestDbSnapcopy(unittest.TestCase):
    def test_invalid_parse_source(self):
        source = "bad_source"
        with self.assertRaises(ValueError):
            parse_source(source)

    def test_valid_parse_source(self):
        s = "us-east-1:my-db"
        source = parse_source(s)

        self.assertIsInstance(source, Source)
        self.assertEqual(source.region, "us-east-1")
        self.assertEqual(source.id, "my-db")

        s = "us-east-1:my-db:with-colons"
        source = parse_source(s)

        self.assertIsInstance(source, Source)
        self.assertEqual(source.region, "us-east-1")
        self.assertEqual(source.id, "my-db:with-colons")

    def test_invalid_parse_destination(self):
        d = "bad_dest"
        with self.assertRaises(ValueError):
            parse_destination("us-east-1", d)

    def test_valid_parse_destination(self):
        source_region = "us-east-1"
        scenario = namedtuple("scenario", ["dest", "region", "name"])
        tests = (
            scenario(":", source_region, None),
            scenario("us-west-1:", "us-west-1", None),
            scenario(":my-snap", source_region, "my-snap"),
            scenario("us-west-1:my-snap", "us-west-1", "my-snap"),
        )

        for t in tests:
            dest = parse_destination(source_region, t.dest)
            self.assertIsInstance(dest, Dest)
            self.assertEqual(dest.region, t.region)
            self.assertEqual(dest.name, t.name)

    def test_sanitize_snapshot_name(self):
        name = "abc@def:ghi"
        r = sanitize_snapshot_name(name)
        self.assertIsInstance(r, str)
        self.assertEqual(r, "abc-def-ghi")

        name = u"abc@def:ghi"
        r = sanitize_snapshot_name(name)
        self.assertIsInstance(r, str)
        self.assertEqual(r, "abc-def-ghi")

    def test_get_snapshot_target_name(self):
        now = datetime.utcfromtimestamp(0)
        r = get_snapshot_target_name(
            Dest("us-east-1", "my-snap"), "source", "us-east-1", now
        )
        self.assertEqual(r, "my-snap")
        r = get_snapshot_target_name(Dest("us-east-1", ""), "source", "us-east-1", now)
        self.assertEqual(r, "source-copy-us-east-1-19700101T000000Z")
