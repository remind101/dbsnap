from dbsnap_verify import handler

def lambda_handler(event, context):
    """The main entrypoint called when our AWS Lambda wakes up."""
    handler(event)
