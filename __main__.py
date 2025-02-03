"""
Juno Innovations - EKS Infrastructure for Orion
"""
# local
from src import JunoAccount, JunoRegion, Cluster, set_repositories, set_profile, set_session

# set the root account
JunoAccount.set_root_account("management_account_name")

# set AWS session and profiles
set_profile("management_iam_user")      # this should be an account that can assume other accounts and have specific permissions to do so
set_session("management_session_name")  # this is a trackable session name

# bootstrap
Cluster.set_bootstrap_repository(
    repository="https://github.com/juno-fx/aws-eks-infrastructure.git",
    path="bootstrap/",
)

# ECR repositories
set_repositories([
    # juno images
    "hubble",
    "kuiper",
    "titan",
    "polaris-workstation",
    "mars",
    "luna",
    "webb",
    "pluto",
    "terra",
    "mercury",
    "genesis"
])


# account and regional deployments
with JunoAccount("deployment_account_name"):
    with JunoRegion("us-east-1", ecr_master=True):
        with Cluster('192.168.0.0') as cluster:
            cluster.add_node_group(
                name="service",
                instances=["c6a.xlarge", "t3.xlarge"],
                capacity_type=cluster.CapacityType.SPOT,
                minimum=1,
                size=1,
                maximum=5,
            )
