"""
Handle region switching in the Juno AWS Organizations
"""

# 3rd
import boto3
from pulumi import ResourceOptions, get_stack
import pulumi_aws as aws

# local
from ..exceptions import ContextNotSet
from ..provider import set_context, get_account
from ..ecr import set_ecr
from .session import get_session, get_profile


# region hooks
# these are functions that will be called when the region is initialized
# they are filtered by stack name. So if you want to only run a hook for
# a specific stack, you can do that.
REGION_HOOKS = {}
PROVIDERS = {}

# Get The Account ID for the organization
def get_current_account_id():
    org = aws.organizations.get_organization()
    return org.master_account_id

# Get The current account ARN to build the environment
def get_current_user_arn():
    client = boto3.client('sts')
    user_arn = client.get_caller_identity().get('Arn')
    return user_arn

# Verify the current account can create the resources
def has_administrator_access(user_name):
    iam_client = boto3.client('iam')
    attached_policies = iam_client.list_attached_user_policies(UserName=user_name)
    for policy in attached_policies['AttachedPolicies']:
        if policy['PolicyName'] == 'AdministratorAccess':
            return True
    return False




class JunoRegion:
    def __init__(self, region: str, ecr_master: bool = False, ecr_sync: bool = False):
        account = get_account()

        # instance variables
        self.ecr_master = ecr_master
        self.ecr_sync = ecr_sync
        self.region = region
        self.account = account.account
        self.context_only = False
        self.account_id = get_current_account_id()
        self.role_arn = f"arn:aws:iam::{self.account_id}:role/{self.account}-OrganizationAccountAccessRole"

        args = dict(profile=get_profile(), allowed_account_ids=[self.account_id], region=region)
        if self.account != "root":
            args["assume_role"] = aws.ProviderAssumeRoleArgs(
                role_arn=self.role_arn, session_name=get_session()
            )

        tag = f"{self.account}-{self.region}-provider"
        if tag not in PROVIDERS:
            PROVIDERS[tag] = aws.Provider(
                f"{self.account}-{self.region}-provider",
                args=aws.ProviderArgs(**args),
                opts=ResourceOptions(parent=account.account_provider),
            )
        else:
            self.context_only = True

        self.provider = PROVIDERS[tag]
        self.partition = account.partition

    def __enter__(self):
        # fail if the context isn't set
        if self.account is None:
            raise ContextNotSet("No JunoAccount set")

        # set region context
        set_context(self)
        if self.context_only:
            return self

        # region hooks
        for hook in REGION_HOOKS.get(get_stack(), []):
            hook()

        # handle ECR
        if self.ecr_sync and self.ecr_master:
            raise ValueError("A region can't be both a sync target and a master.")
        if self.ecr_master:
            set_ecr()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # set region context
        set_context()
