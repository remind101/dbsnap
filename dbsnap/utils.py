def make_tag_dict(tag_list):
    """Returns a dictionary of existing tags.
    Args:
        tag_list (list): a list of tag dicts.
    Returns:
        dict: A dictionary where tag names are keys and tag values are values.
    """
    return {i["Key"]: i["Value"] for i in tag_list}


def get_tags_for_rds_arn(session, rds_arn):
    """Returns a dictionary of existing tags.
    Args:
        rds_arn (str): an RDS resource ARN.
    Returns:
        dict: A dictionary where tag names are keys and tag values are values.
    """
    return make_tag_dict(
        session.list_tags_for_resource(ResourceName=rds_arn)["TagList"]
    )

