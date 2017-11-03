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
    tomorrow_timestamp,
    now_datetime,
    timestamp_to_datetime,
    datetime_to_date_str,
    three_days_prior,
)

import boto3

from sys import stdout
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stdout))


def wait(state_doc, rds_session):
    min_timestamp = state_doc["snapshot_minimum_timestamp"]
    min_datetime = timestamp_to_datetime(min_timestamp)
    logger.info("Looking for a snapshot of {} older then {}".format(
        state_doc["database"],
        datetime_to_date_str(min_datetime)
    ))
    snapshot_desc = get_latest_snapshot(rds_session, state_doc["database"])
    if snapshot_desc["SnapshotCreateTime"] >= min_datetime:
        # if the latest snapshot is older then the minimum, restore it.
        restore(state_doc, rds_session)
    elif min_datetime <= three_days_prior(now_datetime):
        # continue wating for a new snapshot, to restore.
        transition_state(state_doc, "wait")
        logger.info("Did not find a snapshot of {} older then {}".format(
            state_doc["database"],
            datetime_to_date_str(min_datetime)
        ))
        logger.info("Going to sleep.")
    else:
        logger.warning("Alert! we never found a snapshot of {} older then {}".format(
            state_doc["database"],
            datetime_to_date_str(min_datetime)
        ))
        alarm("asdfasdfasdkfjnasdf naskdfn aksdjfn")


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
    # this is janky but the modify operation doesn't happen right away.
    # this is temporary until I can find a better way.
    from time import sleep
    sleep(20)


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
        logger.info(
            "cleaning {tmp_database} subnet group and tmp_password".format(
                **state_doc
            )
        )
        del state_doc["tmp_password"]
        state_count_to_keep = 100
        trim_index = len(state_doc["states"]) - state_count_to_keep
        state_doc["states"] = state_doc["states"][trim_index:]
        state_doc["snapshot_minimum_timestamp"] = tomorrow_timestamp()
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
