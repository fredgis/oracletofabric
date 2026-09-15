"""Readable deployed architecture overview for the repository README."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge, Node, getdiagram
from diagrams.azure.compute import VMLinux, VMWindows
from diagrams.azure.network import PrivateEndpoint
from diagrams.generic.network import Router
from diagrams.onprem.client import User

from common import icon, output_path


GRAPH_ATTR = {
    "splines": "ortho",
    "nodesep": "0.72",
    "ranksep": "0.95",
    "pad": "0.35",
    "fontname": "Segoe UI Semibold",
    "fontsize": "24",
    "bgcolor": "white",
    "compound": "true",
    "newrank": "true",
}

NODE_ATTR = {
    "fontname": "Segoe UI Semibold",
    "fontsize": "20",
    "margin": "0.18",
}

EDGE_ATTR = {
    "fontname": "Segoe UI",
    "fontsize": "16",
    "color": "#39424E",
    "penwidth": "2",
}

AZURE_ATTR = {
    "bgcolor": "#F3F8FD",
    "pencolor": "#0078D4",
    "fontname": "Segoe UI Semibold",
    "fontsize": "22",
    "penwidth": "2.5",
}

VNET_ATTR = {
    "bgcolor": "#EEF7EE",
    "pencolor": "#2E7D32",
    "fontname": "Segoe UI Semibold",
    "fontsize": "20",
    "penwidth": "2.5",
}

SUBNET_ATTR = {
    "bgcolor": "#FBFDFB",
    "pencolor": "#81A784",
    "fontname": "Segoe UI Semibold",
    "fontsize": "18",
    "penwidth": "1.5",
}

FABRIC_ATTR = {
    "bgcolor": "#FAF5FF",
    "pencolor": "#742774",
    "fontname": "Segoe UI Semibold",
    "fontsize": "22",
    "penwidth": "2.5",
}

LEGEND_ATTR = {
    "bgcolor": "#F7F7F7",
    "pencolor": "#9E9E9E",
    "fontname": "Segoe UI",
    "fontsize": "16",
    "penwidth": "1",
}


with Diagram(
    "Oracle to Fabric Demo\nDeployed architecture | Central US",
    filename=output_path("00-readme-overview"),
    show=False,
    direction="TB",
    outformat=["svg", "png", "pdf"],
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    administrator = User("Administrator\nAzure portal")
    bastion = icon(
        "Bastion Developer\nSSH and RDP",
        "azure-bastion.png",
    )

    with Cluster("Azure resource group | FGI-ORACLE", graph_attr=AZURE_ATTR):
        with Cluster("demo-oracle-vnet | 10.60.0.0/16", graph_attr=VNET_ATTR):
            with Cluster(
                "Oracle subnet | 10.60.1.0/24",
                graph_attr=SUBNET_ATTR,
            ):
                oracle_vm = VMLinux(
                    "demo-oracle-vm\n"
                    "Linux 9.8 + Oracle Free\n"
                    "DEMO_DW | private IP"
                )

            with Cluster(
                "Gateway subnet | 10.60.2.0/24",
                graph_attr=SUBNET_ATTR,
            ):
                gateway_vm = VMWindows(
                    "demo-fabric-gateway-vm\n"
                    "Windows 2022 + Fabric gateway\n"
                    "private IP"
                )

            with Cluster(
                "Private endpoint subnet | 10.60.3.0/24",
                graph_attr=SUBNET_ATTR,
            ):
                key_vault = PrivateEndpoint(
                    "Key Vault Private Endpoint\n"
                    "public access disabled"
                )

            nat = Router(
                "NAT Gateway\n"
                "outbound only"
            )

    with Cluster(
        "Microsoft Fabric | FGI-ORACLE workspace | F16",
        graph_attr=FABRIC_ATTR,
    ):
        mirrored_database = icon(
            "DemoOracleMirror\nsnapshot + CDC",
            "mirrored_generic_database_64_item.png",
        )
        lakehouse = icon(
            "DemoLakehouse\nDEMO_DW shortcuts",
            "lakehouse_64_item.png",
        )

    with getdiagram().dot.subgraph() as administration_rank:
        administration_rank.attr(rank="same")
        administration_rank.node(administrator.nodeid)
        administration_rank.node(bastion.nodeid)

    with getdiagram().dot.subgraph() as azure_rank:
        azure_rank.attr(rank="same")
        azure_rank.node(oracle_vm.nodeid)
        azure_rank.node(gateway_vm.nodeid)
        azure_rank.node(key_vault.nodeid)
        azure_rank.node(nat.nodeid)

    with getdiagram().dot.subgraph() as fabric_rank:
        fabric_rank.attr(rank="same")
        fabric_rank.node(mirrored_database.nodeid)
        fabric_rank.node(lakehouse.nodeid)

    administrator >> Edge(
        label="HTTPS 443",
        style="dashed",
        color="#757575",
    ) >> bastion
    bastion >> Edge(
        label="SSH 22",
        style="dashed",
        color="#757575",
    ) >> oracle_vm
    bastion >> Edge(
        label="RDP 3389",
        style="dashed",
        color="#757575",
    ) >> gateway_vm

    gateway_vm >> Edge(
        label="Oracle Net 1521",
    ) >> oracle_vm
    oracle_vm >> Edge(
        label="Private Link 443",
        style="dashed",
        color="#757575",
    ) >> key_vault
    gateway_vm >> Edge(
        label="Private Link 443",
        style="dashed",
        color="#757575",
    ) >> key_vault

    gateway_vm >> Edge(
        label="Relay + HTTPS 443",
    ) >> nat
    nat >> Edge(
        label="Oracle connection",
    ) >> mirrored_database
    mirrored_database >> Edge(
        label="OneLake",
    ) >> lakehouse

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        Node(
            "Solid: data or service path\n"
            "Dashed: administration or secret retrieval\n"
            "Both VMs are private\n"
            "NAT is outbound only",
            shape="note",
            style="filled",
            fillcolor="#FFFFFF",
            color="#9E9E9E",
            fontname="Segoe UI",
            fontsize="14",
            fixedsize="false",
            width="4.2",
            height="1.1",
            margin="0.18",
        )
