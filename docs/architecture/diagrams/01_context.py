"""Target context view for Oracle Database Free to Microsoft Fabric."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import VMLinux, VMWindows
from diagrams.azure.network import OnPremisesDataGateways, VirtualNetworkGateways
from diagrams.generic.network import Router
from diagrams.onprem.client import User
from diagrams.onprem.database import Oracle
from diagrams.onprem.network import Internet

from common import (
    AZURE_TENANT_ATTR,
    EDGE_ATTR,
    FABRIC_ATTR,
    GRAPH_ATTR,
    LEGEND_ATTR,
    NODE_ATTR,
    SUBNET_ATTR,
    VNET_ATTR,
    icon,
    legend,
    output_path,
)


with Diagram(
    "Oracle Database Free to Microsoft Fabric\n01 Context view | Target architecture, not deployed",
    filename=output_path("01-context"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    admin = User("Administration\nworkstation")
    oracle_registry = Internet("Oracle Container\nRegistry")

    with Cluster("Azure tenant | Subscription and region: TBD", graph_attr=AZURE_TENANT_ATTR):
        private_access = VirtualNetworkGateways("P2S VPN or\nExpressRoute\nchoice pending")

        with Cluster("Private VNet | Name and CIDR: TBD", graph_attr=VNET_ATTR):
            with Cluster("AzureBastionSubnet | /26 or larger", graph_attr=SUBNET_ATTR):
                bastion = icon("Azure Bastion Premium\nprivate-only", "azure-bastion.png")

            with Cluster("snet-oracle | CIDR: TBD", graph_attr=SUBNET_ATTR):
                oracle_vm = VMLinux("Oracle Linux VM\nno public IP")
                oracle_db = Oracle("Oracle AI Database 26ai Free\ncontainer and managed disk")

            with Cluster("snet-gateway | CIDR: TBD", graph_attr=SUBNET_ATTR):
                gateway_vm = VMWindows("Windows gateway VM\nno public IP")
                opdg = OnPremisesDataGateways("On-premises data gateway\nstandard mode")

            egress = Router("Controlled outbound access\nNAT Gateway or Azure Firewall")

    with Cluster("Microsoft Fabric | Workspace and capacity: TBD", graph_attr=FABRIC_ATTR):
        fabric = icon("Microsoft Fabric", "fabric_48_color.png")
        workspace = icon("Fabric workspace", "group_workspace_64_non-item.png")
        mirrored_db = icon("Oracle Mirrored Database", "mirrored_generic_database_64_item.png")
        lakehouse = icon("Lakehouse", "lakehouse_64_item.png")

    admin >> Edge(label="Private connectivity", style="dashed", color="#757575") >> private_access
    private_access >> Edge(label="HTTPS 443", style="dashed", color="#757575") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Podman and persistent volume") >> oracle_db
    gateway_vm >> Edge(label="Hosts") >> opdg
    opdg >> Edge(label="Oracle Net on private listener") >> oracle_db

    oracle_vm >> Edge(label="HTTPS 443 outbound") >> egress
    egress >> Edge(label="Pinned image pull") >> oracle_registry
    opdg >> Edge(label="HTTPS 443 outbound") >> egress
    egress >> Edge(label="Azure Relay and Fabric") >> fabric

    fabric >> Edge(label="Control plane", style="dashed", color="#757575") >> workspace
    workspace >> Edge(label="Oracle mirroring") >> mirrored_db
    mirrored_db >> Edge(label="OneLake shortcut") >> lakehouse

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Solid: data or service flow\nDashed: administration or control plane\nTBD: value selected during implementation")
