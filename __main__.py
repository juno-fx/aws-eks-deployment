"""
Juno Innovations - EKS Infrastructure for Orion
"""
# local
from src import JunoAccount, JunoRegion, Cluster, set_repositories, set_profile, set_session

# set the root account
JunoAccount.set_root_account("Alex Hatfield")                 # this is the root account that will be used to manage the other accounts

# set AWS session and profiles
set_profile("cosmos")                                      # this should be an account that can assume other accounts and have specific permissions to do so
set_session("Cosmos")                                  # this is a trackable session name

# bootstrap
Cluster.set_bootstrap_repository(
    repository="https://github.com/juno-fx/aws-eks-deployment.git",     # this is the repository that will be used to bootstrap the cluster
    path="bootstrap/",                                                  # this is the path within the repository that contains the bootstrap helm chart
    ref="main",                                                         # this is the branch or tag that will be used to bootstrap the cluster
    domain="juno-innovations.com"                                                # this is the domain that will be used to create the cluster
)

# ECR repositories
# These are the repositories that will be used to store the images for the
# cluster. If you are planning on bringing your own images, you can disable
# this block.
# set_repositories([
#     # juno images
#     "hubble",
#     "kuiper",
#     "titan",
#     "polaris-workstation",
#     "mars",
#     "luna",
#     "webb",
#     "pluto",
#     "terra",
#     "mercury",
#     "genesis"
# ])


# account and regional deployments
with JunoAccount("Production"):                    # this is the account that will be used to deploy the clusters
    with JunoRegion("us-east-1", ecr_master=True):        # this is the region that the clusters will be deployed to
        pass
        # example private cluster
        with Cluster(private=True) as cluster:
            # standard service node setup
            cluster.add_node_group(
                name="service",
                instances=["c6a.xlarge", "t3.xlarge"],
                capacity_type=cluster.CapacityType.SPOT,
                minimum=1,
                size=1,
                maximum=5,
                labels={
                    "juno-innovations.com/service": "true"
                }
            )
        #
        #     # example render node setup flagged for headless workloads and is GPU enabled
        #     cluster.add_node_group(
        #         gpu=True,
        #         name="render",
        #         instances=[
        #             "m6a.4xlarge",
        #             "m5a.4xlarge",
        #             "m7a.4xlarge",
        #             "r5.2xlarge",
        #             "r6a.2xlarge",
        #             "r7i.2xlarge"
        #         ],
        #         capacity_type=cluster.CapacityType.SPOT,
        #         minimum=0,
        #         size=0,
        #         maximum=4,
        #         labels={
        #             "juno-innovations.com/headless": "true",
        #         },
        #         taints=["juno-innovations.com/headless"]
        #     )
        #
        #     # example render node setup flagged for workstation workloads and is GPU enabled
        #     cluster.add_node_group(
        #         gpu=True,
        #         name="workstation",
        #         instances=[
        #             "m6a.4xlarge",
        #             "m5a.4xlarge",
        #             "m7a.4xlarge",
        #             "r5.2xlarge",
        #             "r6a.2xlarge",
        #             "r7i.2xlarge"
        #         ],
        #         capacity_type=cluster.CapacityType.SPOT,
        #         minimum=0,
        #         size=0,
        #         maximum=4,
        #         labels={
        #             "juno-innovations.com/workstation": "true",
        #         },
        #         taints=["juno-innovations.com/workstation"]
        #     )
        #
        # # example public cluster
        # with Cluster() as cluster:
        #     # standard service node setup
        #     cluster.add_node_group(
        #         name="service",
        #         instances=["c6a.xlarge", "t3.xlarge"],
        #         capacity_type=cluster.CapacityType.SPOT,
        #         minimum=1,
        #         size=1,
        #         maximum=5,
        #         labels={
        #             "juno-innovations.com/service": "true"
        #         }
        #     )
