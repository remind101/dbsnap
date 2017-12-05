from rds_funcs import (
    get_latest_snapshot,
    get_database_description,
    restore_from_latest_snapshot,
    modify_db_instance_for_verify,
    dbsnap_verify_db_id,
    destroy_database,
    destroy_database_subnet_group,
    rds_event_messages,
)

from state_doc import (
    current_state,
    transition_state,
    get_or_create_state_doc,
    clean_state_doc,
)

from time_funcs import (
    tomorrow_timestamp,
    now_datetime,
    timestamp_to_datetime,
    datetime_to_date_str,
    add_days_to_datetime,
)

import boto3

import logging
logger = logging.getLogger(__name__)


def wait(state_doc, rds_session):
    """wait: currently waiting for the next snapshot to appear."""
    min_timestamp = state_doc["snapshot_minimum_timestamp"]
    min_datetime = timestamp_to_datetime(min_timestamp)
    max_datetime = add_days_to_datetime(min_datetime, 3)
    logger.info(
        "Looking for a snapshot of %s older then %s",
        state_doc["database"],
        datetime_to_date_str(min_datetime)
    )
    snapshot_desc = get_latest_snapshot(rds_session, state_doc["database"])
    if snapshot_desc["SnapshotCreateTime"] >= min_datetime:
        # if the latest snapshot is older then the minimum, restore it.
        transition_state(state_doc, "restore")
        restore(state_doc, rds_session)
    elif now_datetime() < max_datetime:
        # continue wating for a new snapshot, to restore.
        transition_state(state_doc, "wait")
        logger.info(
            "Did not find a snapshot of %s older then %s",
            state_doc["database"],
            datetime_to_date_str(min_datetime)
        )
        logger.info("Going to sleep.")
    else:
        # the deadman switch was triggered, we didn't get a new snapshot!
        logger.warning(
            "Alert! we never found a snapshot of %s older then %s",
            state_doc["database"],
            datetime_to_date_str(min_datetime)
        )
        # TODO: call alarm state.


def restore(state_doc, rds_session):
    """restore: currently restoring a copy of the latest
    snapshot into a temporary RDS db instance."""
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    if tmp_db_description is None:
        logger.info(
            "Restoring snapshot of %s to %s",
            state_doc["database"],
            state_doc["tmp_database"]
        )
        subnet_ids = state_doc["database_subnet_ids"]
        if isinstance(sn_ids, basestring):
            subnet_ids = subnet_ids.split(",")
        restore_from_latest_snapshot(
            rds_session, state_doc["database"], subnet_ids
        )
    elif tmp_db_description["DBInstanceStatus"] == "available":
        transition_state(state_doc, "modify")
        modify(state_doc, rds_session)


def modify(state_doc, rds_session):
    """modify: currently modifying the temporary RDS db instance
    settings to allow the dbsnap-verify tool to access it."""
    logger.info(
        "Modifying %s master password and security groups",
        state_doc["tmp_database"]
    )
    security_group_ids = state_doc["database_security_group_ids"]
    if isinstance(sg_ids, basestring):
        security_group_ids = security_group_ids.split(",")
    state_doc["tmp_password"] = modify_db_instance_for_verify(
        rds_session, state_doc["tmp_database"], security_group_ids,
    )
    transition_state(state_doc, "verify")
    verify(state_doc, rds_session)


def verify(state_doc, rds_session):
    """verify: currently verifying the temporary RDS db instance
    using the supplied checks. (not implemented)"""
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    tmp_db_status = tmp_db_description["DBInstanceStatus"]
    tmp_db_event_messages = rds_event_messages(
        rds_session, state_doc["tmp_database"]
    )
    if 'Reset master credentials' in tmp_db_event_messages and tmp_db_status == "available":
        # TODO: this is currently not implemented so we move to cleanup.
        # in the future this code block will actually connect to the endpoint
        # and run SQL query checks defined by the configuration.
        logger.info(
            "Skipping verify of %s, not implemented",
            state_doc["tmp_database"]
        )
        #connection = connect_to_endpoint(db_description["endpoint"])
        #result = run_all_the_tests(connection, state_doc["verfication_checks"])
        #if result:
        #    transition_state(state_doc, "cleanup")
        #else:
        #    transition_state(state_doc, "alarm")
        #    alarm(state_doc, "error")
        transition_state(state_doc, "cleanup")
        cleanup(state_doc, rds_session)


def cleanup(state_doc, rds_session):
    """clean: currently tearing down the temporary RDS db instance
    and anything else we created or modified."""
    tmp_db_description = get_database_description(
        rds_session, state_doc["tmp_database"]
    )
    if tmp_db_description is None:
        # cleanup of db subnet group, tmp_password, and transition to wait.
        logger.info(
            "cleaning %s subnet group and tmp_password",
            state_doc["tmp_database"]
        )
        destroy_database_subnet_group(rds_session, state_doc["tmp_database"])
        # remove tmp_password, clear old states, wait for next snapshot.
        state_doc = clean_state_doc(state_doc)
        # start next snapshot (which could appear tomorrow).
        transition_state(state_doc, "wait")
    elif tmp_db_description["DBInstanceStatus"] == "available":
        logger.info(
            "cleaning / destroying %s",
            state_doc["tmp_database"]
        )
        destroy_database(
            rds_session,
            state_doc["tmp_database"],
            tmp_db_description["DBInstanceArn"]
        )

def alarm(state_doc, rds_session):
    """"alarm: something went wrong we are going to scream about it."""
    # TODO:  trigger an alarm, cloudwatch and optionally datadog.
    # currently not implemented
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
    from sys import stdout
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stdout))
    state_doc = get_or_create_state_doc(event)
    if state_doc is None:
        # A state_doc is None if we receive an invalid or unrelated event
        # from from Cloudwatch or SNS, like an unrelated RDS db instance.
        logger.info("Ignoring unrelated RDS event: %s", event)
    else:
        state_handler = state_handlers[current_state(state_doc)]
        rds_session =  boto3.client(
            "rds", region_name=state_doc["snapshot_region"]
        )
        state_handler(state_doc, rds_session)
