from rds_funcs import (
    get_latest_snapshot,
    get_database_description,
    restore_from_latest_snapshot,
    modify_db_instance_for_verify,
    dbsnap_verify_db_id,
    destroy_database,
    destroy_database_subnet_group,
)

from state_doc import (
    current_state,
    transition_state,
    get_or_create_state_doc,
)

from time_funcs import (
    date_str_to_datetime,
    today_date,
)

import logging
logger = logging.getLogger(__name__)

import boto3
rds = boto3.client("rds", region_name="us-east-1")


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
        transition_state(state_doc, "wait")
        logger.info("Did not find the {snapshot_date} snapshot of {database}".format(**state_doc))
        logger.info("Going to sleep.")

@add_db_description
def restore(state_doc, db_description=None):
    if db_description is None:
        transition_state(state_doc, "restore")
        sn_ids = state_doc["database_sn_ids"]
        if isinstance(sn_ids, basestring):
            sn_ids = sn_ids.split(",")
        restore_from_latest_snapshot(rds, state_doc["database"], sn_ids)
    elif db_description["DBInstanceStatus"] == "available":
        transition_state(state_doc, "modify")
        modify(state_doc, db_description)

@add_db_description
def modify(state_doc, db_description=None):
    sg_ids = state_doc["database_sg_ids"]
    if isinstance(sg_ids, basestring):
        sg_ids = sg_ids.split(",")
    state_doc["tmp_password"] = modify_db_instance_for_verify(
        rds, state_doc["tmp_database"], sg_ids,
    )
    transition_state(state_doc, "verify")

@add_db_description
def verify(state_doc, db_description=None):
    if db_description["DBInstanceStatus"] == "available":
        #connection = connect_to_endpoint(db_description["endpoint"])
        #result = run_all_the_tests(connection, state_doc["verfication_checks"])
        #if result:
        #    transition_state(state_doc, "success")
        #    alarm(state_doc, "success")
        #else:
        #    transition_state(state_doc, "alarm")
        #    alarm(state_doc, "error")
        transition_state(state_doc, "cleanup")
        cleanup(state_doc, db_description)

@add_db_description
def cleanup(state_doc, db_description=None):
    if db_description is None:
        # start waiting for tomorrows date.
        del state_doc["tmp_password"]
        destroy_database_subnet_group(rds, state_doc["tmp_database"])
        transition_state(state_doc, "wait")
    elif db_description["DBInstanceStatus"] == "available":
        destroy_database(rds, state_doc["tmp_database"], db_description["DBInstanceArn"])

def alarm(state_doc):
    # trigger an alarm, maybe cloudwatch or something.
    pass

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
    state_doc = get_or_create_state_doc(config)
    state_handler = state_handlers[current_state(state_doc)]
    state_handler(state_doc)
