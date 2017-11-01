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

import boto3

from sys import stdout
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stdout))


def wait(state_doc, rds_session):
    logger.info("Looking for the {snapshot_date} snapshot of {database}".format(**state_doc))
    description = get_latest_snapshot(rds_session, state_doc["database"])
    if description:
        restore(state_doc, rds_session)
    elif today_date() > date_str_to_datetime(state_doc["snapshot_date"]):
        logger.warning("Alert! we never found the {snapshot_date} snapshot for {database}".format(**state_doc))
        alarm("asdfasdfasdkfjnasdf naskdfn aksdjfn")
    else:
        transition_state(state_doc, "wait")
        logger.info("Did not find the {snapshot_date} snapshot of {database}".format(**state_doc))
        logger.info("Going to sleep.")


def restore(state_doc, rds_session):
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    if tmp_db_description is None:
        logger.info(
            "Restoring snapshot of {database} to {tmp_database}".format(
                **state_doc
            )
        )
        transition_state(state_doc, "restore")
        sn_ids = state_doc["database_sn_ids"]
        if isinstance(sn_ids, basestring):
            sn_ids = sn_ids.split(",")
        restore_from_latest_snapshot(rds_session, state_doc["database"], sn_ids)
    elif tmp_db_description["DBInstanceStatus"] == "available":
        transition_state(state_doc, "modify")
        modify(state_doc, rds_session)


def modify(state_doc, rds_session):
    logger.info(
        "Modifying {tmp_database} master password and security groups".format(
            **state_doc
        )
    )
    sg_ids = state_doc["database_sg_ids"]
    if isinstance(sg_ids, basestring):
        sg_ids = sg_ids.split(",")
    state_doc["tmp_password"] = modify_db_instance_for_verify(
        rds_session, state_doc["tmp_database"], sg_ids,
    )
    transition_state(state_doc, "verify")


def verify(state_doc, rds_session):
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    if tmp_db_description["DBInstanceStatus"] == "available":
        logger.info(
            "Skipping verify of {tmp_database}, not implemented".format(
                **state_doc
            )
        )
        #connection = connect_to_endpoint(db_description["endpoint"])
        #result = run_all_the_tests(connection, state_doc["verfication_checks"])
        #if result:
        #    transition_state(state_doc, "success")
        #    alarm(state_doc, "success")
        #else:
        #    transition_state(state_doc, "alarm")
        #    alarm(state_doc, "error")
        transition_state(state_doc, "cleanup")
        cleanup(state_doc, rds_session)


def cleanup(state_doc, rds_session):
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    if tmp_db_description is None:
        # start waiting for tomorrows date.
        del state_doc["tmp_password"]
        destroy_database_subnet_group(rds_session, state_doc["tmp_database"])
        transition_state(state_doc, "wait")
    elif tmp_db_description["DBInstanceStatus"] == "available":
        logger.info(
            "cleaning / destroying {tmp_database}".format(
                **state_doc
            )
        )
        destroy_database(
            rds_session,
            state_doc["tmp_database"],
            tmp_db_description["DBInstanceArn"]
        )

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

def handler(event):
    """The main entrypoint called from CLI or when our AWS Lambda wakes up."""
    state_doc = get_or_create_state_doc(event)
    if state_doc is None:
        logger.info("Ignoring unrelated RDS event: {}".format(event))
    else:
        state_handler = state_handlers[current_state(state_doc)]
        rds_session =  boto3.client(
            "rds", region_name=state_doc["snapshot_region"]
        )
        state_handler(state_doc, rds_session)
