# pylint: disable=too-few-public-methods,unused-wildcard-import,wildcard-import
"""
Security settings
"""

# std
from typing import List

# 3rd
from pulumi_aws.ec2 import *


# base
class SecuritySpec:
    # spec
    ingress: List[SecurityGroupIngressArgs] = []
    egress: List[SecurityGroupEgressArgs] = []

    # predefined
    OPEN = SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        ipv6_cidr_blocks=["::/0"],
    )
