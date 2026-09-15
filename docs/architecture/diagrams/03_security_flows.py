"""Allowed and blocked security flows for the Oracle to Fabric Demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge, Node
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
    "Oracle to Fabric Demo\n03 Security flows | Deployed controls",
    filename=output_path("03-security-flows"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr={**GRAPH_ATTR, "splines": "spline"},
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    internet = Internet("Public Internet")
    admin = User("Approved administrator")
    oracle_packages = Internet("Oracle package endpoints")

    with Cluster("Azure Demo | Central US", graph_attr=AZURE_TENANT_ATTR):
        portal = ManagementPortal("Azure portal")
        bastion = icon("Bastion Developer\nshared pool", "azure-bastion.png")

        blocked_ingress = Node(
            "Blocked by design\nNo workload public IP\nNo Internet NSG ingress",
            shape="note",
            style="filled",
            fillcolor="#FFF2F0",
            color="#C62828",
            fontcolor="#7F1D1D",
            fixedsize="false",
            labelloc="c",
            margin="0.16",
        )

        with Cluster("demo-oracle-vnet | Private workloads", graph_attr=VNET_ATTR):
            with Cluster("snet-demo-oracle", graph_attr=SUBNET_ATTR):
                oracle_vm = VMLinux("demo-oracle-vm")
                oracle_db = Oracle("Oracle Database Free")

            with Cluster("snet-demo-gateway", graph_attr=SUBNET_ATTR):
                gateway_vm = VMWindows("demo-fabric-gateway-vm")
                opdg = OnPremisesDataGateways("On-premises data gateway")

            nat = Router("NAT Gateway\noutbound only")

        nat_ip = PublicIpAddresses("One NAT public IP\nno inbound path")

    with Cluster("Microsoft Fabric", graph_attr=FABRIC_ATTR):
        fabric = icon("Fabric service", "fabric_48_color.png")
        mirrored_db = icon("Demo Oracle Mirror", "mirrored_generic_database_64_item.png")

    internet >> Edge(label="No route to workloads", color="#C62828", style="dashed", penwidth="2") >> blocked_ingress

    admin >> Edge(label="HTTPS 443", color="#2E7D32", penwidth="2") >> portal
    portal >> Edge(label="Browser session", style="dashed", color="#757575") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Native Oracle service", color="#2E7D32", penwidth="2") >> oracle_db
    gateway_vm >> Edge(label="Hosts", color="#2E7D32", penwidth="2") >> opdg
    opdg >> Edge(label="Oracle Net\nprivate listener", color="#2E7D32", penwidth="2") >> oracle_db

    oracle_vm >> Edge(label="HTTPS 443 outbound", color="#1565C0") >> nat
    opdg >> Edge(label="HTTPS 443 outbound", color="#1565C0") >> nat
    nat >> Edge(label="SNAT only", color="#1565C0") >> nat_ip
    nat_ip >> Edge(label="Pinned RPM", color="#1565C0") >> oracle_packages
    nat_ip >> Edge(label="Azure Relay and Fabric", color="#1565C0") >> fabric
    fabric >> Edge(label="Replicates into", color="#2E7D32", penwidth="2") >> mirrored_db

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Green: allowed management or private flow\nBlue: required outbound-only flow\nRed dashed: blocked Internet ingress\nNo VPN Gateway")
