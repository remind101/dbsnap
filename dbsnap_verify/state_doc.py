from os import environ

import json

import boto3

from time_funcs import (
    today_timestamp,
    now_timestamp,
)
from rds_funcs import dbsnap_verify_db_id


def current_state(state_doc):
    return state_doc["states"][-1]["state"]


def get_state_doc_bucket(config):
    return environ.get("STATE_DOC_BUCKET", config.get("state_doc_bucket", None))


def set_state_doc_in_path(state_doc):
    with open(state_doc["state_doc_path"], 'w') as json_file:
        json.dump(state_doc, json_file, indent=2)


def upload_state_doc(state_doc):
    state_doc_json = json.dumps(state_doc, indent=2)
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=get_state_doc_bucket(state_doc),
        Key=state_doc_s3_key(state_doc["database"]),
        Body=state_doc_json,
    )


def set_state_doc_in_s3(state_doc):
    upload_state_doc(state_doc)
    return state_doc


def state_doc_s3_key(database):
    return "state-doc-{}.json".format(database)


def download_state_doc(config):
    s3 = boto3.client("s3")
    s3_object = s3.get_object(
        Bucket=get_state_doc_bucket(config),
        Key=state_doc_s3_key(config["database"]),
    )
    # download state_doc json from s3 and stick it into a string.
    state_doc_json = s3_object["Body"].read()
    # turn json into a dict and return it.
    return json.loads(state_doc_json)


def create_state_doc(config):
    state_doc = config
    state_doc["states"] = []
    state_doc["snapshot_minimum_timestamp"] = today_timestamp()
    state_doc["tmp_database"] = dbsnap_verify_db_id(state_doc["database"])
    return transition_state(state_doc, "wait")


def get_state_doc_in_s3(config):
    """get the state_doc in S3 or None."""
    try:
        return download_state_doc(config)
    except boto3.client("s3").exceptions.NoSuchKey:
        return None


def get_or_create_state_doc_in_s3(config):
    """get (or create if missing) the state_doc in S3."""
    state_doc = get_state_doc_in_s3(config)
    if state_doc is None:
        state_doc = create_state_doc(config)
    return state_doc


def get_or_create_state_doc_in_path(config):
    try:
        with open(config["state_doc_path"], 'r') as json_file:
            state_doc = json.load(json_file)
    except IOError:
        state_doc = create_state_doc(config)
    return state_doc


def state_doc_persistence(config):
    """str: "state_doc_bucket" or "state_doc_path" or raises exception."""
    if get_state_doc_bucket(config) and "state_doc_path" in config:
        msg = "Choose either `state_doc_bucket` or `state_doc_path` not both."
        raise Exception(msg)
    elif get_state_doc_bucket(config):
        return "state_doc_bucket"
    elif "state_doc_path" in config:
        return "state_doc_path"


def transition_state(state_doc, new_state):
    state_doc["states"].append(
        {"state" : new_state, "timestamp" : now_timestamp()}
    )
    if state_doc_persistence(state_doc) == "state_doc_bucket":
        set_state_doc_in_s3(state_doc)
    else:
        set_state_doc_in_path(state_doc)
    return state_doc


def get_or_create_state_doc(config):
    if "database" not in config:
        # try to get state_doc for a RDS event, intead of config event.
        try:
            event_message = json.loads(
                config["Records"][0]["Sns"]["Message"]
            )
            database_id = event_message["Source ID"][14:]
            rds_event_message = event_message["Event Message"]
            return get_state_doc_in_s3(
                {
                    "database": database_id,
                    "rds_event_latest_message": rds_event_message,
                }
            )
        except KeyError:
            pass
    else:
        persistence = state_doc_persistence(config)
        if persistence == "state_doc_path":
            return get_or_create_state_doc_in_path(config)
        elif persistence == "state_doc_bucket":
            return get_or_create_state_doc_in_s3(config)
