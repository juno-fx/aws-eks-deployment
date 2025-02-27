# 3rd
from pulumi import ResourceOptions
from pulumi_aws.iam import (
    Role,
    RoleArgs,
    Policy,
    PolicyArgs,
    RolePolicyAttachment,
    RolePolicyAttachmentArgs,
)
from pulumi_aws.ec2 import Subnet

# local
from .provider import context_prefix
from . import policies


def build_node_role(cluster: str, parent: Subnet) -> Role:
    """
    Build the node role for the EKS cluster
    """
    base_node_role = Role(
        f"{context_prefix()}-base-node-role",
        RoleArgs(assume_role_policy=policies.get_role("sts")),
        opts=ResourceOptions(parent=parent),
    )

    ebs_policy = Policy(
        f"{context_prefix()}-base-node-ebs-policy",
        PolicyArgs(policy=policies.get_policy("eks-ebs")),
        opts=ResourceOptions(parent=base_node_role),
    )

    alb_policy = Policy(
        f"{context_prefix()}-base-node-alb-policy",
        PolicyArgs(policy=policies.get_policy("eks-ingress")),
        opts=ResourceOptions(parent=base_node_role),
    )

    efs_policy = Policy(
        f"{context_prefix()}-base-node-efs-policy",
        PolicyArgs(policy=policies.get_policy("eks-efs")),
        opts=ResourceOptions(parent=base_node_role),
    )

    ecr_policy = Policy(
        f"{context_prefix()}-base-node-ecr-policy",
        PolicyArgs(policy=policies.get_policy("ecr")),
        opts=ResourceOptions(parent=base_node_role),
    )

    autoscale_policy = Policy(
        f"{context_prefix()}-base-node-autoscale-policy",
        PolicyArgs(policy=policies.get_policy("autoscale").replace("JUNO-CLUSTER", cluster)),
        opts=ResourceOptions(parent=base_node_role),
    )

    # attached policies
    node_policies = [
        policies.ECR_RO,
        policies.EKS_CNI,
        policies.EKS_WORKER,
        policies.EFS_CSI,
        autoscale_policy.arn,
        ebs_policy.arn,
        efs_policy.arn,
        ecr_policy.arn,
        alb_policy.arn,
    ]

    for idx, policy in enumerate(node_policies):
        RolePolicyAttachment(
            f"{context_prefix()}-base-node-policy-attachment-{idx}",
            RolePolicyAttachmentArgs(policy_arn=policy, role=base_node_role),
            opts=ResourceOptions(parent=ecr_policy),
        )
    return base_node_role
