"""
Handle VPC setup for a target region.
"""

# std
import base64
import os
from ipaddress import IPv4Network
from json import dumps
from typing import Union, Dict, List
from enum import Enum

# 3rd
from pulumiverse_time import Sleep
from pulumi import ResourceOptions
from pulumi_aws.ec2 import (
    RouteTable,
    InternetGateway,
    RouteTableAssociation,
    Route,
)
from pulumi_aws.iam import Role
import pulumi_kubernetes as k8s
import pulumi_kubernetes.helm.v3 as helm
from pulumi import InvokeOptions
from pulumi_aws import get_availability_zones
from pulumi_aws.ec2.vpc import Vpc
from pulumi_aws.ec2 import Subnet, NatGateway, Eip, VpcIpv4CidrBlockAssociation
from pulumi_eks import (
    Cluster as EksCluster,
    ClusterArgs,
    KubeconfigOptionsArgs,
    ManagedNodeGroupArgs,
    ManagedNodeGroup,
    ClusterNodeGroupOptionsArgs,
)
from pulumi_aws.eks import NodeGroupTaintArgs
import pulumi_command as cmd
import pulumi_aws as aws
from pulumi_aws.efs import FileSystem, MountTarget
from pulumi_aws.ec2.security_group import SecurityGroup

# local
from .node_role import build_node_role
from .provider import juno_resource, get_context, context_prefix, set_cluster
from .security import SecuritySpec
from .context.session import get_profile


# pylint: disable=invalid-name
azs = get_availability_zones(state="available").names


if not os.environ.get("GIT_USER") or not os.environ.get("GIT_PASS"):
    raise ValueError("GIT_USER and GIT_PASS must be set in the environment for GitHub")


class Cluster:
    """
    Regional Cluster
    """

    BOOTSTRAP_REPOSITORY = None
    BOOTSTRAP_PATH = "."
    BOOTSTRAP_REF = "main"

    @staticmethod
    def set_bootstrap_repository(repository: str, path: str, ref: str):
        """
        Set the bootstrap repository
        """
        Cluster.BOOTSTRAP_REPOSITORY = repository
        Cluster.BOOTSTRAP_PATH = path
        Cluster.BOOTSTRAP_REF = ref

    class CapacityType(Enum):
        SPOT = "SPOT"
        ON_DEMAND = "ON_DEMAND"

    def __init__(self, private: bool = False):
        """
        Setup regional Cluster
        """
        set_cluster('private' if private else 'public')

        # instance variables
        self.context = get_context()
        self.private = private

        # VPC CIDR's
        self.production_cidr = "192.168.0.0/18"
        self.dropped_cidr = "192.168.64.0/24"
        self.service_cidr = "192.168.65.0/24"

        # networking
        self.vpc: Union[Vpc, None] = None
        self.production_subnet: Union[Subnet, None] = None
        self.dropped_subnet: Union[Subnet, None] = None
        self.service_subnet: Union[Subnet, None] = None
        self.route_table: Union[RouteTable, None] = None

        # cluster
        name = '-private' if self.private else '-public'
        self.cluster: Union[EksCluster, None] = None
        self.cluster_name: str = f"{context_prefix()}{name}"
        self.base_node_role: Union[Role, None] = None
        self.kubeconfig_opts = KubeconfigOptionsArgs(profile_name=get_profile())
        self.nodes = []
        self.argo_provider: Union[k8s.Provider, None] = None
        self.k8s_provider: Union[k8s.Provider, None] = None
        self.file_system: Union[FileSystem, None] = None

        # zones
        self.availability_zones = get_availability_zones(
            state="available", opts=InvokeOptions(provider=self.context.provider)
        ).names
        self.production_zone = self.availability_zones[0]
        self.dropped_zone = self.availability_zones[1]

        print(f"Cluster: {self.cluster_name}")
        print(f"\tPrivate: {self.private}")
        print(f"\tProduction CIDR: {self.production_cidr}")
        print(f"\tService CIDR: {self.service_cidr}")
        print(f"\tDropped CIDR: {self.dropped_cidr}")
        print(f"\tUsable IP Addresses: {IPv4Network(self.production_cidr).num_addresses - 2}")

        # initialize

        self.build_storage()
        self.build_networking()
        self.build_mount()
        self.build_node_role()

    def __enter__(self):
        self.start_cluster()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.nodes:
            self.bootstrap()
        set_cluster(None)

    def build_storage(self):
        """
        Build storage resources for this Region
        """
        self.file_system = FileSystem(
            availability_zone_name=self.production_zone,
            **juno_resource("efs"),
        )

    def build_mount(self):
        """
        Build the mount target
        """
        MountTarget(
            subnet_id=self.production_subnet.id,
            file_system_id=self.file_system.id,
            security_groups=[
                SecurityGroup(
                    vpc_id=self.vpc.id,
                    ingress=[SecuritySpec.OPEN],
                    egress=[SecuritySpec.OPEN],
                    **juno_resource(
                        "efs-mount-sg",
                        opts=dict(depends_on=[self.file_system], parent=self.file_system),
                    ),
                ).id
            ],
            **juno_resource(
                "efs-mount",
                opts=dict(depends_on=[self.file_system], parent=self.file_system),
                no_tags=True,
            ),
        )

    def create_subnet(self, name: str, cidr: str, zone: str, private: bool = False, associate=True):
        """
        Create a subnet
        """
        parent = self.vpc
        if associate:
            association = VpcIpv4CidrBlockAssociation(
                vpc_id=self.vpc.id,
                cidr_block=cidr,
                **juno_resource(
                    f"{name}-association",
                    opts=dict(depends_on=[self.vpc], parent=self.vpc),
                    no_tags=True,
                ),
            )
            parent = association

        return Subnet(
            vpc_id=self.vpc.id,
            cidr_block=cidr,
            map_public_ip_on_launch=not private,
            availability_zone=zone,
            **juno_resource(name, opts=dict(depends_on=[parent], parent=parent)),
        )

    def build_service_networking(self, internet_gateway) -> NatGateway:
        """
        Build out networking for the service subnet to serve private subnets
        """
        # service subnet needs to have public access so traffic can be routed through the NAT gateway
        self.service_subnet = self.create_subnet(
            "service", self.service_cidr, self.production_zone, private=False
        )

        # service subnet which has internet for the NAT
        eip = Eip(
            **juno_resource(
                "nat-eip", opts=dict(depends_on=[internet_gateway], parent=internet_gateway)
            ),
        )
        service_route_table = RouteTable(
            vpc_id=self.vpc.id,
            **juno_resource("service-routing-table", opts=dict(parent=self.service_subnet)),
        )
        Route(
            route_table_id=service_route_table.id,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=internet_gateway.id,
            **juno_resource(
                "service-internet-gateway-route",
                opts=dict(parent=service_route_table),
                no_tags=True,
            ),
        )
        RouteTableAssociation(
            route_table_id=service_route_table.id,
            subnet_id=self.service_subnet.id,
            **juno_resource(
                "service-connect-routing-association",
                opts=dict(parent=service_route_table),
                no_tags=True,
            ),
        )

        return NatGateway(
            subnet_id=self.service_subnet.id,
            allocation_id=eip.id,
            **juno_resource("nat-gateway", opts=dict(depends_on=[eip], parent=eip)),
        )

    def build_networking(self):
        """
        Build networking for this Region
        """
        self.vpc = Vpc(
            enable_dns_hostnames=True,
            enable_dns_support=True,
            cidr_block=self.production_cidr,
            **juno_resource("vpc"),
        )

        # Production subnet
        self.production_subnet = self.create_subnet(
            "production", self.production_cidr, self.production_zone, private=self.private, associate=False
        )

        # this subnet doesn't need to ever be public
        self.dropped_subnet = self.create_subnet(
            "dropped", self.dropped_cidr, self.dropped_zone, private=True
        )

        # setup internet gateway
        internet_gateway = InternetGateway(
            vpc_id=self.vpc.id,
            **juno_resource("internet-gateway", opts=dict(depends_on=[self.vpc], parent=self.vpc)),
        )

        # setup routing table
        production_route_table = RouteTable(
            vpc_id=self.vpc.id,
            **juno_resource("production-routing-table", opts=dict(parent=self.production_subnet)),
        )

        RouteTableAssociation(
            route_table_id=production_route_table.id,
            subnet_id=self.production_subnet.id,
            **juno_resource(
                "production-connect-routing-association",
                opts=dict(parent=production_route_table),
                no_tags=True,
            ),
        )

        if self.private:
            nat = self.build_service_networking(internet_gateway)
            Route(
                route_table_id=production_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                nat_gateway_id=nat.id,
                **juno_resource(
                    "production-internet-gateway-route",
                    opts=dict(parent=nat),
                    no_tags=True,
                ),
            )
        else:
            Route(
                route_table_id=production_route_table.id,
                destination_cidr_block="0.0.0.0/0",
                gateway_id=internet_gateway.id,
                **juno_resource(
                    "production-internet-gateway-route",
                    opts=dict(parent=production_route_table),
                    no_tags=True,
                ),
            )

    def build_node_role(self):
        """
        Build the node role
        """
        self.base_node_role = build_node_role(self.cluster_name, self.production_subnet)

    def start_cluster(self):
        """
        Start the cluster
        """
        self.cluster = EksCluster(
            self.cluster_name,
            ClusterArgs(
                vpc_id=self.vpc.id,
                name=self.cluster_name,
                public_subnet_ids=[],
                private_subnet_ids=[self.production_subnet.id, self.dropped_subnet.id],
                node_associate_public_ip_address=False,
                skip_default_node_group=True,
                endpoint_private_access=True,
                endpoint_public_access=True,
                instance_roles=[self.base_node_role],
                create_oidc_provider=True,
                use_default_vpc_cni=True,
                node_group_options=ClusterNodeGroupOptionsArgs(
                    node_associate_public_ip_address=False,
                ),
                provider_credential_opts=KubeconfigOptionsArgs(
                    profile_name=get_profile(),
                    role_arn=self.context.role_arn,
                ),
            ),
            opts=ResourceOptions(parent=self.base_node_role, provider=self.context.provider),
        )

        cmd.local.Command(
            f"{context_prefix()}-export-kubeconfig",
            cmd.local.CommandArgs(
                create=f"echo $KUBECONFIG >  {self.cluster_name}.kubeconfig",
                environment={"KUBECONFIG": self.cluster.get_kubeconfig()},
            ),
            opts=ResourceOptions(parent=self.cluster),
        )

        self.k8s_provider = k8s.Provider(
            f"{context_prefix()}-deployment-provider",
            kubeconfig=self.cluster.kubeconfig,
            enable_server_side_apply=True,
            opts=ResourceOptions(parent=self.cluster, depends_on=self.nodes),
        )

        self.argo_provider = k8s.Provider(
            f"{context_prefix()}-argo-provider",
            namespace="argocd",
            kubeconfig=self.cluster.kubeconfig,
            opts=ResourceOptions(parent=self.cluster, depends_on=self.nodes),
        )

        k8s.yaml.ConfigFile(
            f"{context_prefix()}-aws-auth",
            file="https://s3.us-west-2.amazonaws.com/amazon-eks/docs/eks-console-full-access.yaml",
            resource_prefix=context_prefix(),
            opts=ResourceOptions(parent=self.cluster, provider=self.k8s_provider),
        )

        k8s.core.v1.ConfigMap(
            f"{context_prefix()}-aws-auth-config",
            data={
                "mapUsers": f"""- groups:
  - system:masters
  userarn: arn:aws:iam::{get_context().account_id}:user/eks-viewer
  username: eks-viewer""",
                "mapRoles": f"""- groups:
  - system:masters
  rolearn: {get_context().role_arn}
  username: system:node:{{EC2PrivateDNSName}}""",
            },
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name="aws-auth",
                namespace="kube-system",
                annotations={
                    "pulumi.com/patchForce": "true",
                },
            ),
            opts=ResourceOptions(parent=self.cluster, provider=self.k8s_provider),
        )

    def bootstrap(self):
        """
        Bootstrap the cluster
        """
        namespace = k8s.core.v1.Namespace(
            f"{context_prefix()}-argocd-namespace",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name="argocd", annotations={"pulumi.com/skipAwait": "true"}
            ),
            opts=ResourceOptions(
                parent=self.cluster, provider=self.k8s_provider, depends_on=self.nodes
            ),
        )

        # deploy argocd
        argo = k8s.yaml.ConfigFile(
            f"{context_prefix()}-argocd",
            file="https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml",
            resource_prefix=context_prefix(),
            opts=ResourceOptions(parent=namespace, provider=self.argo_provider),
        )

        # Begin Juno Bootstrap
        k8s.core.v1.Secret(
            f"{context_prefix()}-github-secret",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name="github-token",
                namespace="argocd",
                labels={"argocd.argoproj.io/secret-type": "repo-creds"},
                annotations={
                    "pulumi.com/patchForce": "true",
                },
            ),
            string_data={
                "url": "https://github.com",
                "username": os.environ.get("GIT_USER"),
                "password": os.environ.get("GIT_PASS"),
            },
            opts=ResourceOptions(parent=argo, provider=self.argo_provider),
        )

        aws.eks.Addon(
            f"{context_prefix()}-vpc-cni",
            cluster_name=self.cluster_name,
            addon_name="vpc-cni",
            resolve_conflicts_on_create="OVERWRITE",
            opts=ResourceOptions(parent=self.cluster, provider=self.context.provider),
            configuration_values=dumps({"enableNetworkPolicy": "true"}),
        )

        aws.eks.Addon(
            f"{context_prefix()}-aws-ebs-csi-driver",
            cluster_name=self.cluster_name,
            addon_name="aws-ebs-csi-driver",
            resolve_conflicts_on_create="OVERWRITE",
            opts=ResourceOptions(parent=self.cluster, provider=self.context.provider),
        )

        aws.eks.Addon(
            f"{context_prefix()}-aws-efs-csi-driver",
            cluster_name=self.cluster_name,
            addon_name="aws-efs-csi-driver",
            resolve_conflicts_on_create="OVERWRITE",
            opts=ResourceOptions(parent=self.cluster, provider=self.context.provider),
        )

        chart_path = f"{os.path.dirname(__file__)}/chart"

        args = dict(
            path=chart_path,
            namespace="argocd",
            values={
                "repository": Cluster.BOOTSTRAP_REPOSITORY,
                "path": Cluster.BOOTSTRAP_PATH,
                "ref": Cluster.BOOTSTRAP_REF,
                "region": get_context().region,
                "file_system": self.file_system.dns_name.apply(lambda x: x),
                "account": get_context().account,
                "subnet": self.production_subnet.id,
                "account_id": get_context().account_id,
                "private": 'true' if self.private else 'false',
            },
        )
        tag = context_prefix()
        args["resource_prefix"] = tag
        args["values"]["prefix"] = f"{tag}-"


        # Pulumi's k8s ConfigFile resource is not respecting the depends_on order and the
        # CRD's for ArgoCD are not being set into for the Helm Chart which causes it to
        # fail in a race condition. To get around this, I am setting a 2 minute sleep to
        # hold the helm chart back and allow pulumi to traverse the dependencies correctly
        # from the ConfigFile.
        wait = Sleep(
            f"{context_prefix()}-wait-for-argocd-crds",
            create_duration="5m",
            opts=ResourceOptions(
                parent=argo
            )
        )

        helm.Chart(
            f"{context_prefix()}-juno-bootstrap",
            helm.LocalChartOpts(**args),
            opts=ResourceOptions(
                provider=self.argo_provider,
                depends_on=[wait],
                parent=argo
            ),
        )

    def add_node_group(
        self,
        name: str,
        instances: List[str],
        capacity_type: CapacityType,
        size: int,
        maximum: int = None,
        minimum: int = None,
        resource_name: str = None,
        labels: Dict[str, str] = None,
    ):
        """
        Create a node group for the project cluster
        """
        if maximum is None:
            maximum = size

        if minimum is None:
            minimum = size

        if not labels:
            labels = {}

        instances.sort()
        args = dict(
            cluster=self.cluster,
            node_role_arn=self.base_node_role.arn,
            capacity_type=capacity_type.value,
            instance_types=instances,
            disk_size=150,
            subnet_ids=[self.production_subnet.id],
            labels=labels,
            taints=[],
            scaling_config={
                "desired_size": size,
                "min_size": minimum,
                "max_size": maximum,
            },
            tags={
                "Name": f"{context_prefix()}-{name}-node",
                "region": self.context.region,
                "workload-type": name,
                "k8s.io/cluster-autoscaler/enabled": "true",
                f"k8s.io/cluster-autoscaler/{self.cluster_name}": "owned",
            },
            ami_type="AL2_x86_64",
        )

        if name in ("workstation", "render"):
            args["ami_type"] = "AL2_x86_64_GPU"
            args["disk_size"] = 70
            args["taints"].append(
                NodeGroupTaintArgs(effect="NO_SCHEDULE", key=f"junovfx/{name}", value="true")
            )

        # noinspection PyTypeChecker
        if resource_name is not None:
            name = resource_name

        self.nodes.append(
            ManagedNodeGroup(
                f"{context_prefix()}-{name}-nodes",
                ManagedNodeGroupArgs(**args),
                opts=ResourceOptions(depends_on=self.cluster, parent=self.cluster),
            )
        )
