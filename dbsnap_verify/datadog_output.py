import time

# https://docs.datadoghq.com/integrations/amazon_lambda/#lambda-metrics
DATADOG_METRIC_TYPES = {"count", "gauge", "histogram", "check"}

# https://github.com/DataDog/datadogpy/blob/master/datadog/api/constants.py
class CheckStatus(object):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3
    ALL = (OK, WARNING, CRITICAL, UNKNOWN)


def now_timestamp():
    return time.time()


def validate_metric_type(metric_type):
    if metric_type not in DATADOG_METRIC_TYPES:
        raise Exception(
            "Invalid datadog metric_type {}, must be {}".format(
                 metric_type, DATADOG_METRIC_TYPES
            )
        )


def format_metric_tags(metric_tags):
    if not metric_tags:
        return metric_tags

    elif isinstance(metric_tags, list):
        return "#" + ",".join(metric_tags)

    elif isinstance(metric_tags, dict):
        return "#" + ",".join(
            ["{}:{}".format(key, value) for key, value in metric_tags.items()]
        )

    if not metric_tags.startswith("#"):
        return "#" + metric_tags

    return metric_tags


def datadog_lambda_metric_output(metric_name, metric_value, metric_type="count", metric_tags=""):
    validate_metric_type(metric_type)
    return "MONITORING|{}|{}|{}|{}|{}".format(
        now_timestamp(),
        metric_value,
        metric_type,
        metric_name,
        format_metric_tags(metric_tags),
    )


def datadog_lambda_check_output(metric_name, metric_value, metric_tags=""):
    if not isinstance(metric_value, int):
        metric_value = CheckStatus.__dict__[metric_value]
    return datadog_lambda_metric_output(
        metric_name=metric_name,
        metric_value=metric_value,
        metric_type="check",
        metric_tags=metric_tags,
    )
