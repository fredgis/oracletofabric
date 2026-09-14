"""Oracle snapshot and CDC data flow for the Oracle to Fabric Demo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagrams import Cluster, Diagram, Edge
from diagrams.azure.compute import VMWindows
from diagrams.azure.network import OnPremisesDataGateways
from diagrams.onprem.client import Client
from diagrams.onprem.database import Oracle

from common import (
    EDGE_ATTR,
    FABRIC_ATTR,
    GRAPH_ATTR,
    LEGEND_ATTR,
    NODE_ATTR,
    icon,
    legend,
    output_path,
)


with Diagram(
    "Oracle to Fabric Demo\n04 Data flows | Snapshot, CDC, and Lakehouse access",
    filename=output_path("04-data-flows"),
    show=False,
    direction="LR",
    outformat=["svg", "png", "pdf"],
    graph_attr=GRAPH_ATTR,
    node_attr=NODE_ATTR,
    edge_attr=EDGE_ATTR,
):
    with Cluster("Azure Demo private VNet"):
        oracle_db = Oracle(
            "Oracle AI Database 26ai Free\n"
            "DEMO_DW.DIM_DATE\nDEMO_DW.DIM_CUSTOMER\nDEMO_DW.DIM_PRODUCT\n"
            "DEMO_DW.DIM_STORE\nDEMO_DW.FACT_SALES"
        )
        gateway_vm = VMWindows("demo-fabric-gateway-vm")
        opdg = OnPremisesDataGateways("On-premises data gateway\nOracle Client for Microsoft Tools")

    with Cluster("Microsoft Fabric | Existing F16 capacity", graph_attr=FABRIC_ATTR):
        fabric = icon("Microsoft Fabric", "fabric_48_color.png")
        workspace = icon("Existing workspace", "group_workspace_64_non-item.png")
        mirrored_db = icon("Demo Oracle Mirror\nDelta tables in OneLake", "mirrored_generic_database_64_item.png")
        sql_endpoint = icon("SQL analytics endpoint", "database_sql_32_filled.png")
        lakehouse = icon("Demo Lakehouse\nOneLake shortcuts", "lakehouse_64_item.png")

    consumers = Client("SQL and Spark consumers")

    gateway_vm >> Edge(label="Hosts") >> opdg
    oracle_db >> Edge(label="Initial snapshot and LogMiner CDC\nOracle Net over private VNet") >> opdg
    opdg >> Edge(label="Outbound HTTPS 443") >> fabric
    fabric >> Edge(label="Workspace control plane", style="dashed", color="#757575") >> workspace
    workspace >> Edge(label="Creates and manages", style="dashed", color="#757575") >> mirrored_db
    mirrored_db >> Edge(label="Native SQL access") >> sql_endpoint
    mirrored_db >> Edge(label="OneLake shortcuts\nno second data copy") >> lakehouse
    sql_endpoint >> Edge(label="T-SQL") >> consumers
    lakehouse >> Edge(label="Spark and SQL") >> consumers

    with Cluster("Legend", graph_attr=LEGEND_ATTR):
        legend("Solid: data path\nDashed: Fabric control plane\nDemo Oracle Mirror is the replication target\nDemo Lakehouse reads through shortcuts")
