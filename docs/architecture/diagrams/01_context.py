"""Deployed context view for the Oracle to Fabric Demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import VMLinux, VMWindows
from diagrams.azure.general import ManagementPortal
from diagrams.azure.network import OnPremisesDataGateways, PublicIpAddresses
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
    "Oracle to Fabric Demo\n01 Context view | Deployed and validated",
    filename=output_path("01-context"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    admin = User("Administrator")
    oracle_packages = Internet("Oracle public\npackage repositories")

    with Cluster("Azure Demo | Central US", graph_attr=AZURE_TENANT_ATTR):
        portal = ManagementPortal("Azure portal")
        bastion = icon("Azure Bastion Developer\nshared and free", "azure-bastion.png")

        with Cluster("demo-oracle-vnet | 10.60.0.0/16", graph_attr=VNET_ATTR):
            with Cluster("snet-demo-oracle | 10.60.1.0/24", graph_attr=SUBNET_ATTR):
                oracle_vm = VMLinux("demo-oracle-vm\nno public IP")
                oracle_db = Oracle("Oracle AI Database 26ai Free\nnative RPM and managed disk")

            with Cluster("snet-demo-gateway | 10.60.2.0/24", graph_attr=SUBNET_ATTR):
                gateway_vm = VMWindows("demo-fabric-gateway-vm\nno public IP")
                opdg = OnPremisesDataGateways("On-premises data gateway\nstandard mode")

            nat = Router("demo-egress-nat\noutbound only")

        nat_ip = PublicIpAddresses("One NAT public IP\noutbound only")

    with Cluster("Microsoft Fabric | Existing F16 capacity", graph_attr=FABRIC_ATTR):
        fabric = icon("Microsoft Fabric", "fabric_48_color.png")
        workspace = icon("Existing workspace", "group_workspace_64_non-item.png")
        mirrored_db = icon("Demo Oracle Mirror", "mirrored_generic_database_64_item.png")
        lakehouse = icon("DemoLakehouse\nschema-enabled", "lakehouse_64_item.png")

    admin >> Edge(label="HTTPS 443", style="dashed", color="#757575") >> portal
    portal >> Edge(label="Browser session", style="dashed", color="#757575") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Native service and persistent data") >> oracle_db
    gateway_vm >> Edge(label="Hosts") >> opdg
    opdg >> Edge(label="Oracle Net on private listener") >> oracle_db

    oracle_vm >> Edge(label="HTTPS 443 outbound") >> nat
    opdg >> Edge(label="HTTPS 443 outbound") >> nat
    nat >> Edge(label="SNAT only") >> nat_ip
    nat_ip >> Edge(label="Pinned RPM download") >> oracle_packages
    nat_ip >> Edge(label="Azure Relay and Fabric") >> fabric

    fabric >> Edge(label="Control plane", style="dashed", color="#757575") >> workspace
    workspace >> Edge(label="Oracle mirroring") >> mirrored_db
    mirrored_db >> Edge(label="OneLake shortcuts") >> lakehouse

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Solid: data or service flow\nDashed: Azure management flow\nNo VM public IP\nOne outbound-only NAT public IP")
