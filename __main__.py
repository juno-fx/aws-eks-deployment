"""
Juno Innovations - EKS Infrastructure for Orion
"""
from dotenv import load_dotenv
load_dotenv()
# local
from src import JunoAccount, JunoRegion, Cluster, set_repositories, set_profile, set_session

# set the root account
JunoAccount.set_root_account("management_account_name")                 # this is the root account that will be used to manage the other accounts

# set AWS session and profiles
set_profile("management_iam_user")                                      # this should be an account that can assume other accounts and have specific permissions to do so
set_session("management_session_name")                                  # this is a trackable session name

# bootstrap
Cluster.set_bootstrap_repository(
    repository="https://github.com/juno-fx/aws-eks-deployment.git",     # this is the repository that will be used to bootstrap the cluster
    path="bootstrap/",                                                  # this is the path within the repository that contains the bootstrap helm chart
    ref="main",                                                         # this is the branch or tag that will be used to bootstrap the cluster
    domain="example.com"                                                # this is the domain that will be used to create the cluster
)

# ECR repositories
# These are the repositories that will be used to store the images for the
# cluster. If you are planning on bringing your own images, you can disable
# this block.
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





# account in standalone in personal setup 
# Steps to create a role with the option to select a trusted entity (current account or remote account):
# 
# 1. Navigate to the IAM Console:
#    Open the AWS Management Console, go to the IAM (Identity and Access Management) service,
#    and select "Roles" from the left-hand navigation pane. Click on the "Create role" button
#    to start the role creation process.
# 
# 2. Select Trusted Entity:
#    Choose the type of trusted entity for the role. You can select "AWS account" to specify
#    either the current account or a remote account. If you choose "Another AWS account," you
#    will need to enter the Account ID of the remote account.
# 
# 3. Define Permissions:
#    Attach the necessary permissions policies to the role. These policies define what actions
#    the role can perform. Make sure that the define role can create VPC , Nodegroup , EKS , internet gateway Security group and IAM roles with the account 
# 
# 4. Configure Role Settings:
#    Provide a name and description for the role, and review the trust policy. The trust policy
#    specifies which entities (accounts) are allowed to assume the role



# Those value are necessary on user account without organization role
# But is usefull for standolone practice of when someone grant an assume role to their account 
assume_role_name =  "JunoAdmin"


# Stand Alone Example For personal account not link to an organization
#with JunoAccount("deployment_account_name" ,  admin_role=assume_role_name ):                    # this is the account that will be used to deploy the clusters and also the the role it will assume at creation 
#    with JunoRegion("us-east-1", ecr_master=True ,  admin_role=assume_role_name  ):        # this is the region that the clusters will be deployed to it need the assume role name to follow along an do impersonation 
#        pass

# Stand Alone Example with permission to assume another oganization roles 
#with JunoAccount("deployment_account_name" , account_id="changemetospecificaccountid" ,  admin_role=assume_role_name ):                    # this is the account that will be used to deploy the clusters and also the the role it will assume at creation 
#    with JunoRegion("us-east-1", ecr_master=True ,  admin_role=assume_role_name  ):        # this is the region that the clusters will be deployed to it need the assume role name to follow along an do impersonation 
#        pass


# account and regional deployments
with JunoAccount("deployment_account_name"):                    # this is the account that will be used to deploy the clusters
    with JunoRegion("us-east-1", ecr_master=True):        # this is the region that the clusters will be deployed to
        pass
        # # example private cluster
        # with Cluster(private=True) as cluster:
        #     # standard service node setup
        #     cluster.add_node_group(
        #         name="service",
        #         instances=["c6a.xlarge", "t3.xlarge"],
        #         capacity_type=cluster.CapacityType.SPOT,
        #         minimum=2,
        #         size=2,
        #         maximum=5,
        #         labels={
        #             "juno-innovations.com/service": "true"
        #         }
        #     )
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
