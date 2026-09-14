"""Allowed and blocked security flows for the target architecture."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge, Node
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
    "Oracle Database Free to Microsoft Fabric\n03 Security flows | Target controls, not deployed",
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
    oracle_registry = Internet("Oracle Container\nRegistry")

    with Cluster("Azure tenant | Subscription and region: TBD", graph_attr=AZURE_TENANT_ATTR):
        private_access = VirtualNetworkGateways("P2S VPN or ExpressRoute")

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

        with Cluster("Private VNet | No workload public IP", graph_attr=VNET_ATTR):
            with Cluster("AzureBastionSubnet", graph_attr=SUBNET_ATTR):
                bastion = icon("Azure Bastion Premium\nprivate-only", "azure-bastion.png")

            with Cluster("snet-oracle", graph_attr=SUBNET_ATTR):
                oracle_vm = VMLinux("Oracle Linux VM")
                oracle_db = Oracle("Oracle Database Free")

            with Cluster("snet-gateway", graph_attr=SUBNET_ATTR):
                gateway_vm = VMWindows("Windows gateway VM")
                opdg = OnPremisesDataGateways("On-premises data gateway")

            egress = Router("Controlled egress\nNAT or Firewall")

    with Cluster("Microsoft Fabric", graph_attr=FABRIC_ATTR):
        fabric = icon("Fabric service", "fabric_48_color.png")
        mirrored_db = icon("Oracle Mirrored Database", "mirrored_generic_database_64_item.png")

    internet >> Edge(label="No route to workloads", color="#C62828", style="dashed", penwidth="2") >> blocked_ingress

    admin >> Edge(label="Approved private path", color="#2E7D32", penwidth="2") >> private_access
    private_access >> Edge(label="HTTPS 443", color="#2E7D32", penwidth="2") >> bastion
    bastion >> Edge(label="SSH", style="dashed", color="#757575") >> oracle_vm
    bastion >> Edge(label="RDP", style="dashed", color="#757575") >> gateway_vm

    oracle_vm >> Edge(label="Local container runtime", color="#2E7D32", penwidth="2") >> oracle_db
    gateway_vm >> Edge(label="Hosts", color="#2E7D32", penwidth="2") >> opdg
    opdg >> Edge(label="Oracle Net\nprivate listener", color="#2E7D32", penwidth="2") >> oracle_db

    oracle_vm >> Edge(label="HTTPS 443 outbound", color="#1565C0") >> egress
    egress >> Edge(label="Pinned image pull", color="#1565C0") >> oracle_registry
    opdg >> Edge(label="HTTPS 443 outbound", color="#1565C0") >> egress
    egress >> Edge(label="Azure Relay and Fabric", color="#1565C0") >> fabric
    fabric >> Edge(label="Replicates into", color="#2E7D32", penwidth="2") >> mirrored_db

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Green: allowed private flow\nBlue: required controlled outbound flow\nRed dashed: blocked Internet ingress\nGrey dashed: management flow")
