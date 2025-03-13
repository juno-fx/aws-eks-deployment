"""
Handle account switching in the Juno AWS Organizations
"""

# 3rd
import boto3
from pulumi import get_stack, InvokeOptions
import pulumi_aws as aws

# local
from ..account import eks_node_role
from ..provider import set_account
from .session import get_session

# Juno org

# Get The Account ID for the organization
def get_current_account_id():
    org = aws.organizations.get_organization()
    return org.master_account_id

# account hooks
# these are functions that will be called when the account is initialized
# they are filtered by stack name. So if you want to only run a hook for
# a specific stack, you can do that.
ACCOUNT_HOOKS = {
    "network": [eks_node_role],
}


class JunoAccount:
    ROOT_ACCOUNT = None

    @staticmethod
    def set_root_account(account):
        JunoAccount.ROOT_ACCOUNT = account

    def __init__(self, account: str, admin_role: str = "OrganizationAccountAccessRole", account_id: str = None):
        # instance variables
        self.account = "root" if account == JunoAccount.ROOT_ACCOUNT else account
        
        # Get user ID if account not specified 
        self.account_id = account_id if account_id else get_current_account_id()
        
        args = dict(allowed_account_ids=[self.account_id])
        if self.account != "root":
            args["assume_role"] = aws.ProviderAssumeRoleArgs(
                role_arn=f"arn:aws:iam::{self.account_id}:role/{admin_role}",
                session_name=get_session(),
            )

        self.account_provider = aws.Provider(
            f"{self.account}-provider",
            aws.ProviderArgs(**args),
        )
        self.partition = aws.get_partition(opts=InvokeOptions(provider=self.account_provider))

    def __enter__(self):
        # set account context
        set_account(self)

        # account hooks
        for hook in ACCOUNT_HOOKS.get(get_stack(), []):
            hook()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # set account context
        set_account()
