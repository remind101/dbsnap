from time import time

import datetime

import json

from rds_funcs import (
    get_latest_snapshot,
    get_database_description,
    restore_from_latest_snapshot,
    modify_db_instance_for_verify,
    dbsnap_verify_db_id,
    destroy_database,
    destroy_database_subnet_group,
)

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch1 = logging.StreamHandler()
logger.addHandler(ch1)

import boto3
s3 = boto3.client("s3")
rds = boto3.client("rds", region_name="us-east-1")


def now_timestamp():
    return int(time())

def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)

def now_datetime():
    return datetime.datetime.now()

def today_date():
    return now_datetime()

def tomorrow_date():
    return(now_datetime() + datetime.timedelta(days=1))

def datetime_to_date_str(dt):
    return dt.strftime("%Y-%m-%d")

def date_str_to_datetime(date_str):
    return datetime.datetime(*map(int, date_str.split("-")))

def add_db_description(function):
    def wrapper(state_doc, db_description=None):
        if db_description is None:
            db_description = get_database_description(rds, state_doc["tmp_database"])
        function(state_doc, db_description)
    return wrapper

def wait(state_doc):
    logger.info("Looking for the {snapshot_date} snapshot of {database}".format(**state_doc))
    description = get_latest_snapshot(rds, state_doc["database"])
    if description:
        restore(state_doc)
    elif today_date() > date_str_to_datetime(state_doc["snapshot_date"]):
        logger.warning("Alert! we never found the {snapshot_date} snapshot for {database}".format(**state_doc))
        alarm("asdfasdfasdkfjnasdf naskdfn aksdjfn")
    else:
        set_state_doc_in_s3(state_doc, "wait")
        logger.info("Did not find the {snapshot_date} snapshot of {database}".format(**state_doc))
        logger.info("Going to sleep.")

@add_db_description
def restore(state_doc, db_description=None):
    if db_description is None:
        set_state_doc_in_s3(state_doc, "restore")
        sn_ids = state_doc["database_sn_ids"]
        if isinstance(sn_ids, basestring):
            sn_ids = sn_ids.split(",")
        restore_from_latest_snapshot(rds, state_doc["database"], sn_ids)
    elif db_description["DBInstanceStatus"] == "available":
        set_state_doc_in_s3(state_doc, "modify")
        modify(state_doc, db_description)

@add_db_description
def modify(state_doc, db_description=None):
    sg_ids = state_doc["database_sg_ids"]
    if isinstance(sg_ids, basestring):
        sg_ids = sg_ids.split(",")
    state_doc["tmp_password"] = modify_db_instance_for_verify(
        rds, state_doc["tmp_database"], sg_ids,
    )
    set_state_doc_in_s3(state_doc, "verify")

@add_db_description
def verify(state_doc, db_description=None):
    if db_description["DBInstanceStatus"] == "available":
        #connection = connect_to_endpoint(db_description["endpoint"])
        #result = run_all_the_tests(connection, state_doc["verfication_checks"])
        #if result:
        #    set_state_doc_in_s3(state_doc, "success")
        #    alarm(state_doc, "success")
        #else:
        #    set_state_doc_in_s3(state_doc, "alarm")
        #    alarm(state_doc, "error")
        set_state_doc_in_s3(state_doc, "cleanup")
        cleanup(state_doc, db_description)

@add_db_description
def cleanup(state_doc, db_description=None):
    if db_description is None:
        # start waiting for tomorrows date.
        del state_doc["tmp_password"]
        destroy_database_subnet_group(rds, state_doc["tmp_database"])
        set_state_doc_in_s3(state_doc, "wait")
    elif db_description["DBInstanceStatus"] == "available":
        destroy_database(rds, state_doc["tmp_database"], db_description["DBInstanceArn"])

def alarm(state_doc):
    # trigger an alarm, maybe cloudwatch or something.
    pass

def upload_state_doc(state_doc):
    state_doc_json = json.dumps(state_doc, indent=2)
    s3.put_object(
        Bucket=state_doc["state_doc_bucket"],
        Key=state_doc_s3_key(state_doc["database"]),
        Body=state_doc_json,
    )

def set_state_doc_in_s3(state_doc, new_state):
    if "states" not in state_doc:
        state_doc["states"] = []
    state_doc["states"].append(
        {
            "state" : new_state,
            "timestamp" : now_timestamp(),
        }
    )
    upload_state_doc(state_doc)
    return state_doc

def state_doc_s3_key(database):
    return "state-doc-{}.json".format(database)

def download_state_doc(config):
    s3_object = s3.get_object(
        Bucket=config["state_doc_bucket"],
        Key=state_doc_s3_key(config["database"]),
    )
    # download state_doc json from s3 and stick it into a string.
    state_doc_json = s3_object["Body"].read()
    # turn json into a dict and return it.
    return json.loads(state_doc_json)

def get_or_create_state_doc_in_s3(config):
    """get (or create if missing) the state_doc in S3."""
    try:
        state_doc = download_state_doc(config)
    except s3.exceptions.NoSuchKey:
        state_doc = config
        state_doc["snapshot_date"] = datetime_to_date_str(tomorrow_date())
        state_doc["tmp_database"] = dbsnap_verify_db_id(state_doc["database"])
        state_doc = set_state_doc_in_s3(state_doc, "wait")
    return state_doc

def current_state(state_doc):
    return state_doc["states"][-1]["state"]

state_handlers = {
  "wait": wait,
  "restore": restore,
  "modify": modify,
  "verify": verify,
  "cleanup": cleanup,
  "alarm": alarm,
}

def handler(config):
    """The main entrypoint called from CLI or when our AWS Lambda wakes up."""
    state_doc = get_or_create_state_doc_in_s3(config)
    state_handler = state_handlers[current_state(state_doc)]
    state_handler(state_doc)
