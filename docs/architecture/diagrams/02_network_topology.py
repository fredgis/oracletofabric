"""Target Azure network topology with unresolved deployment values marked TBD."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import VMLinux, VMWindows
from diagrams.azure.network import (
    DNSPrivateZones,
    NetworkSecurityGroupsClassic,
    OnPremisesDataGateways,
    PrivateEndpoint,
    RouteTables,
    VirtualNetworkGateways,
)
from diagrams.azure.security import KeyVaults
from diagrams.generic.network import Router
from diagrams.onprem.client import User
from diagrams.onprem.database import Oracle
from diagrams.onprem.network import Internet

from common import (
    AZURE_TENANT_ATTR,
    EDGE_ATTR,
    GRAPH_ATTR,
    LEGEND_ATTR,
    NODE_ATTR,
    REGION_ATTR,
    SUBNET_ATTR,
    SUBSCRIPTION_ATTR,
    VNET_ATTR,
    icon,
    legend,
    output_path,
)


with Diagram(
    "Oracle Database Free to Microsoft Fabric\n02 Network topology | Target, region and CIDRs TBD",
    filename=output_path("02-network-topology"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr={**GRAPH_ATTR, "splines": "spline"},
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    admin = User("Administration\nworkstation")
    public_services = Internet("Oracle and Microsoft\npublic service endpoints")

    with Cluster("Azure tenant: TBD", graph_attr=AZURE_TENANT_ATTR):
        with Cluster("Subscription: TBD", graph_attr=SUBSCRIPTION_ATTR):
            with Cluster("Region: TBD", graph_attr=REGION_ATTR):
                private_access = VirtualNetworkGateways("P2S VPN or ExpressRoute\nchoice pending")

                with Cluster("Private VNet | Name and CIDR: TBD", graph_attr=VNET_ATTR):
                    with Cluster("AzureBastionSubnet | /26 or larger", graph_attr=SUBNET_ATTR):
                        bastion = icon("Azure Bastion Premium\nprivate-only", "azure-bastion.png")

                    with Cluster("snet-oracle | CIDR: TBD", graph_attr=SUBNET_ATTR):
                        oracle_vm = VMLinux("Oracle Linux VM\nno public IP")
                        oracle_db = Oracle("Oracle Database Free\nprivate listener")

                    with Cluster("snet-gateway | CIDR: TBD", graph_attr=SUBNET_ATTR):
                        gateway_vm = VMWindows("Windows gateway VM\nno public IP")
                        opdg = OnPremisesDataGateways("On-premises\ndata gateway")

                    with Cluster("snet-private-endpoints | CIDR: TBD", graph_attr=SUBNET_ATTR):
                        vault_pe = PrivateEndpoint("Key Vault\nPrivate Endpoint")

                    private_dns = DNSPrivateZones("Private DNS\nKey Vault and Oracle names")
                    nsgs = NetworkSecurityGroupsClassic("Subnet NSGs\nrules: planned")
                    routes = RouteTables("Route tables\nroutes: planned")
                    egress = Router("Controlled outbound access\nNAT or Firewall\nchoice pending")

                key_vault = KeyVaults("Azure Key Vault")

    fabric = icon("Microsoft Fabric\npublic service endpoints", "fabric_48_color.png")

    admin >> Edge(label="Private connectivity", style="dashed", color="#757575") >> private_access
    private_access >> Edge(style="dashed", color="#757575") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Hosts") >> oracle_db
    gateway_vm >> Edge(label="Hosts") >> opdg
    opdg >> Edge(label="Oracle Net\nconfigured private port") >> oracle_db

    vault_pe >> Edge(label="Private Link") >> key_vault
    private_dns >> Edge(label="Resolves vault", style="dashed", color="#757575") >> vault_pe
    private_dns >> Edge(label="Resolves Oracle", style="dashed", color="#757575") >> opdg

    nsgs >> Edge(style="dashed", color="#757575") >> bastion
    nsgs >> Edge(style="dashed", color="#757575") >> oracle_vm
    nsgs >> Edge(style="dashed", color="#757575") >> gateway_vm
    routes >> Edge(label="Default route", style="dashed", color="#757575") >> egress

    oracle_vm >> Edge(label="HTTPS 443 outbound") >> egress
    opdg >> Edge(label="HTTPS 443 outbound") >> egress
    egress >> public_services
    egress >> fabric

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Solid: network or data path\nDashed: management, DNS, or policy\nNo VM public IP and no direct Internet ingress")
