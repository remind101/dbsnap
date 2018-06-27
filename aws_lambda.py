from os import environ
import logging
log_level = environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger("dbsnap")
logger.setLevel(log_level)

from dbsnap_verify import handler

def lambda_handler(event, context):
    """The main entrypoint called when our AWS Lambda wakes up."""
    handler(event)
