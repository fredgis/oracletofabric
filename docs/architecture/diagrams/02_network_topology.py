"""Deployed Azure network topology for the Oracle to Fabric Demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import VMLinux, VMWindows
from diagrams.azure.general import ManagementPortal
from diagrams.azure.network import (
    DNSPrivateZones,
    NetworkSecurityGroupsClassic,
    OnPremisesDataGateways,
    PrivateEndpoint,
    PublicIpAddresses,
    RouteTables,
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
    "Oracle to Fabric Demo\n02 Network topology | Deployed in Central US",
    filename=output_path("02-network-topology"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr={**GRAPH_ATTR, "splines": "spline"},
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    admin = User("Administrator")
    oracle_services = Internet("Oracle and Microsoft\npublic endpoints")

    with Cluster("Azure tenant | Identifier not stored", graph_attr=AZURE_TENANT_ATTR):
        with Cluster("Subscription | Identifier not stored", graph_attr=SUBSCRIPTION_ATTR):
            with Cluster("Central US", graph_attr=REGION_ATTR):
                portal = ManagementPortal("Azure portal")
                bastion = icon("demo-bastion\nDeveloper SKU", "azure-bastion.png")

                with Cluster("demo-oracle-vnet | 10.60.0.0/16", graph_attr=VNET_ATTR):
                    with Cluster("snet-demo-oracle | 10.60.1.0/24", graph_attr=SUBNET_ATTR):
                        oracle_vm = VMLinux("demo-oracle-vm\nno public IP")
                        oracle_db = Oracle("Oracle Database Free\nprivate listener")

                    with Cluster("snet-demo-gateway | 10.60.2.0/24", graph_attr=SUBNET_ATTR):
                        gateway_vm = VMWindows("demo-fabric-gateway-vm\nno public IP")
                        opdg = OnPremisesDataGateways("On-premises\ndata gateway")

                    with Cluster("snet-demo-private-endpoints | 10.60.3.0/24", graph_attr=SUBNET_ATTR):
                        vault_pe = PrivateEndpoint("Key Vault\nPrivate Endpoint")

                    private_dns = DNSPrivateZones("Private DNS\nKey Vault and Oracle names")
                    nsgs = NetworkSecurityGroupsClassic("Demo subnet NSGs")
                    routes = RouteTables("Demo route tables")
                    nat = Router("demo-egress-nat\noutbound only")

                nat_ip = PublicIpAddresses("One Standard public IP\nNAT only")
                key_vault = KeyVaults("Demo Key Vault")

    fabric = icon("Microsoft Fabric\npublic service endpoints", "fabric_48_color.png")

    admin >> Edge(label="HTTPS 443", style="dashed", color="#757575") >> portal
    portal >> Edge(label="Browser session", style="dashed", color="#757575") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Native Oracle service") >> oracle_db
    gateway_vm >> Edge(label="Hosts") >> opdg
    opdg >> Edge(label="Oracle Net\nprivate port") >> oracle_db

    vault_pe >> Edge(label="Private Link") >> key_vault
    private_dns >> Edge(label="Resolves vault", style="dashed", color="#757575") >> vault_pe
    private_dns >> Edge(label="Resolves Oracle", style="dashed", color="#757575") >> opdg

    nsgs >> Edge(style="dashed", color="#757575") >> oracle_vm
    nsgs >> Edge(style="dashed", color="#757575") >> gateway_vm
    routes >> Edge(label="Default route", style="dashed", color="#757575") >> nat

    oracle_vm >> Edge(label="HTTPS 443 outbound") >> nat
    opdg >> Edge(label="HTTPS 443 outbound") >> nat
    nat >> Edge(label="SNAT") >> nat_ip
    nat_ip >> oracle_services
    nat_ip >> fabric

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Solid: network or data path\nDashed: management, DNS, or policy\nNo workload public IP\nOne outbound-only NAT public IP")
