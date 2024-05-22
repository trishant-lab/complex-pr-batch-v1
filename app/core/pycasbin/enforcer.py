import os
from functools import lru_cache

import casbin

dirname = os.path.dirname(os.path.abspath(__file__))
enforcer = casbin.Enforcer(os.path.join(dirname, "./model.conf"), os.path.join(dirname, "./policy.csv"))


@lru_cache(maxsize=100)
def _get_policy_group_roles(policy_group: str) -> set:
    policy_groups = enforcer.get_filtered_named_grouping_policy("g", 0, policy_group)
    return {role for (_, role) in policy_groups}


def role_match_func(request_roles: list[str], policy_group: str) -> bool:
    """
    :param request_roles: list of roles from the request
    :param policy_group: name of the policy group
    :return: True if matched, False otherwise
    """
    return bool(_get_policy_group_roles(policy_group).intersection(request_roles))


@lru_cache(maxsize=200)
def _get_split_path(path: str) -> list[str]:
    return path.lstrip("/").split("/")


def route_match_func(req_path: str, policy_path: str) -> bool:
    """
    Matches url path pattern with path string.
    Path pattern is not wild card.
    eg:
        /api/v1/users -> /api/v1/users
        /api/v1/users/{userId} -> /api/v1/users/123
        /api/v1/users/{userId}/group -> /api/v1/users/123/group
        /api/v1/users/{userId}/group/{groupId} -> /api/v1/users/123/group/456
        /api/v1/users/{userId}/group/{userId} -> /api/v1/users/123/group/123
    """
    pattern_list = _get_split_path(policy_path)
    value_list = req_path.lstrip("/").split("/")
    if len(pattern_list) != len(value_list):
        return False

    path_param_map = {}
    for pattern, value in zip(pattern_list, value_list, strict=True):
        if pattern.startswith("{") and pattern.endswith("}"):
            param_name = pattern[1:-1]
            if param_name in path_param_map and path_param_map[param_name] != value:
                return False
            path_param_map[param_name] = value
        elif pattern != value:
            return False
    return True


enforcer.add_function("roleMatch", role_match_func)
enforcer.add_function("routeMatch", route_match_func)
