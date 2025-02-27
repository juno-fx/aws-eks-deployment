"""
ECR Handler
"""

# std
from typing import List

# 3rd
from pulumi_aws.ecr import (
    Repository,
    RepositoryImageScanningConfigurationArgs,
    LifecyclePolicy,
    ReplicationConfiguration,
    ReplicationConfigurationReplicationConfigurationArgs,
    ReplicationConfigurationReplicationConfigurationRuleDestinationArgs,
    ReplicationConfigurationReplicationConfigurationRuleArgs,
)

# local
from .provider import juno_resource, get_context


REPOSITORIES = []
ECR_MASTER = {}


def set_ecr() -> "ECR":
    """
    Get the ECR handler
    """
    account = get_context().account_id
    ecr = ECR_MASTER.get(account)
    if ecr is None:
        ecr = ECR_MASTER[account] = ECR()
    else:
        raise Exception("ECR already set! Can't have multiple ECRs in the same account.")
    return ecr


def get_ecr() -> "ECR":
    """
    Get the ECR handler
    """
    account = get_context().account_id
    ecr = ECR_MASTER.get(account)
    if ecr is None:
        raise Exception("ECR not set! You need to set a preceding region as the ECR master.")
    return ecr


def set_repositories(repos: List[str]):
    """
    Set the repositories for the ECR handler
    """
    global REPOSITORIES
    REPOSITORIES = repos


class ECR:
    """
    Handles the creation, lifecycle policies and replication for ECR Repositories
    """

    def __init__(self):
        self.repos = {}
        self.primary_context = get_context()
        for repo in REPOSITORIES:
            repository = Repository(
                image_scanning_configuration=RepositoryImageScanningConfigurationArgs(
                    scan_on_push=False,
                ),
                image_tag_mutability="MUTABLE",
                force_delete=True,
                name=repo,
                **juno_resource(repo),
            )

            # clean up policy
            LifecyclePolicy(
                repository=repository.name,
                policy="""{
                            "rules": [
                                {
                                    "rulePriority": 1,
                                    "description": "Expire images older than 1 days",
                                    "selection": {
                                        "tagStatus": "untagged",
                                        "countType": "sinceImagePushed",
                                        "countUnit": "days",
                                        "countNumber": 1
                                    },
                                    "action": {
                                        "type": "expire"
                                    }
                                }
                            ]
                        }
                        """,
                **juno_resource(f"{repo}-lifecycle", dict(parent=repository), no_tags=True),
            )

            self.repos[repo] = repository

    def replicate_here(self):
        """
        Replicate the ECR repositories to the current region
        """
        target_context = get_context()

        ReplicationConfiguration(
            replication_configuration=ReplicationConfigurationReplicationConfigurationArgs(
                rules=[
                    ReplicationConfigurationReplicationConfigurationRuleArgs(
                        destinations=[
                            ReplicationConfigurationReplicationConfigurationRuleDestinationArgs(
                                region=target_context.region,
                                registry_id=target_context.account_id,
                            )
                        ]
                    )
                ]
            ),
            **juno_resource(
                "replication",
                dict(provider=self.primary_context.provider),
                no_tags=True,
            ),
        )
