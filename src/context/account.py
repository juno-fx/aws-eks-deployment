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

    def __init__(self, account: str):
        # instance variables
        self.account = "root" if account == JunoAccount.ROOT_ACCOUNT else account
        # self.account_object = [acct for acct in organization.accounts if acct.name == account][0]
        self.account_id = get_current_account_id()
        if has_administrator_access(self.account):
            current_user_arn = get_current_user_arn()
            role = aws.iam.Role(
                '{self.account}-OrganizationAccountAccessRole',
                assume_role_policy=f"""
                {{
                    "Version": "2012-10-17",
                    "Statement": [
                        {{
                            "Effect": "Allow",
                            "Principal": {{
                                "AWS": "{current_user_arn}"
                            }},
                            "Action": "sts:AssumeRole"
                        }}
                    ]
                }}
                """
            )
            admin_policy_attachment = aws.iam.RolePolicyAttachment(
                'adminPolicyAttachment',
                role=role.name,
                policy_arn='arn:aws:iam::aws:policy/AdministratorAccess'
            )
        else:
            raise ValueError("Please Create user with the default aws roles an permission for the deployment ")
        

        args = dict(allowed_account_ids=[self.account_id])
        if self.account != "root":
            args["assume_role"] = aws.ProviderAssumeRoleArgs(
                role_arn=f"arn:aws:iam::{self.account_id}:role/{self.account}-OrganizationAccountAccessRole",
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
