# std
import json
import os


EKS_WORKER = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
EKS_CNI = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
ECR_RO = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
EFS_CSI = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"


def get_policy(name: str) -> str:
    """
    Get a policy by name
    """
    policy = os.path.abspath(f"{__file__}/../custom_policies/{name}.json")
    with open(policy, "r", encoding="utf-8") as policy_file:
        return policy_file.read()


def get_role(name: str) -> str:
    """
    Get a role by name
    """
    role = os.path.abspath(f"{__file__}/../custom_roles/{name}.json")
    with open(role, "r", encoding="utf-8") as role_file:
        return json.loads(role_file.read())
