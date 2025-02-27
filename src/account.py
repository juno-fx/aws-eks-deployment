"""
Setup IAM for the account level of Juno
"""

# std
import os
from typing import List
from json import loads

# 3rd
from pulumi import ResourceOptions
from pulumi_aws.iam import Policy, Role, RolePolicyAttachment


def load_custom_policies() -> List[Policy]:
    """
    Load custom policies into the account
    """
    # need to do this here because of the circular import
    from .provider import juno_account_resource  # noqa: PLC0415

    policies = []
    custom_policies = os.path.abspath(f"{__file__}/../../custom_policies")

    for custom_policy in os.listdir(custom_policies):
        # load policy from json file
        with open(
            os.path.join(custom_policies, custom_policy), "r", encoding="utf-8"
        ) as policy_file:
            policy = loads(policy_file.read())

        name = f'{custom_policy.split(".")[0]}-policy'
        policies.append(Policy(policy=policy, **juno_account_resource(name)))
    return policies


def load_custom_roles() -> List[Role]:
    """
    Load custom roles into the account
    """
    # need to do this here because of the circular import
    from .provider import juno_account_resource  # noqa: PLC0415

    roles = []
    custom_roles = os.path.abspath(f"{__file__}/../../custom_roles")

    for custom_role in os.listdir(custom_roles):
        # load policy from json file
        with open(os.path.join(custom_roles, custom_role), "r", encoding="utf-8") as role_file:
            policy = loads(role_file.read())

        name = f'{custom_role.split(".")[0]}-role'
        roles.append(Role(assume_role_policy=policy, **juno_account_resource(name)))
    return roles


def eks_node_role() -> Role:
    """
    Create a role for EKS nodes
    """
    # need to do this here because of the circular import :(
    from .provider import juno_account_resource, get_account  # noqa: PLC0415

    account = get_account().account

    node_role = Role(
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Effect": "Allow",
                    "Sid": ""
                }
            ]
        }""",
        **juno_account_resource("eks-node-role"),
    )

    policies = [policy.arn for policy in load_custom_policies()]
    policies.append("arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy")
    policies.append("arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy")
    policies.append("arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly")

    for idx, policy in enumerate(policies):
        RolePolicyAttachment(
            f"{account}-attachment-{idx}",
            policy_arn=policy,
            role=node_role,
            opts=ResourceOptions(parent=node_role),
        )

    return node_role
