"""Shared paths and visual settings for the architecture diagrams."""

from pathlib import Path

from diagrams import Node
from diagrams.custom import Custom


ARCHITECTURE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ARCHITECTURE_DIR / "rendered"
ICON_DIR = ARCHITECTURE_DIR / "icons"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_ATTR = {
    "splines": "ortho",
    "nodesep": "0.65",
    "ranksep": "0.95",
    "pad": "0.45",
    "fontname": "Segoe UI",
    "fontsize": "11",
    "bgcolor": "white",
    "compound": "true",
    "newrank": "true",
}

NODE_ATTR = {
    "fontname": "Segoe UI",
    "fontsize": "10",
}

EDGE_ATTR = {
    "fontname": "Segoe UI",
    "fontsize": "9",
    "color": "#424242",
}

AZURE_TENANT_ATTR = {
    "bgcolor": "#F3F8FD",
    "pencolor": "#0078D4",
    "fontname": "Segoe UI Semibold",
    "fontsize": "14",
    "penwidth": "2",
}

SUBSCRIPTION_ATTR = {
    "bgcolor": "#F8FBFE",
    "pencolor": "#4F9BD4",
    "fontname": "Segoe UI Semibold",
    "fontsize": "13",
    "penwidth": "2",
}

REGION_ATTR = {
    "bgcolor": "#FCFDFE",
    "pencolor": "#85B7DC",
    "fontname": "Segoe UI Semibold",
    "fontsize": "12",
    "penwidth": "2",
}

VNET_ATTR = {
    "bgcolor": "#EEF7EE",
    "pencolor": "#2E7D32",
    "fontname": "Segoe UI Semibold",
    "fontsize": "12",
    "penwidth": "2",
}

SUBNET_ATTR = {
    "bgcolor": "#FAFCFA",
    "pencolor": "#81A784",
    "fontname": "Segoe UI",
    "fontsize": "11",
    "penwidth": "1.5",
}

FABRIC_ATTR = {
    "bgcolor": "#FAF5FF",
    "pencolor": "#742774",
    "fontname": "Segoe UI Semibold",
    "fontsize": "13",
    "penwidth": "2",
}

LEGEND_ATTR = {
    "bgcolor": "#F7F7F7",
    "pencolor": "#9E9E9E",
    "fontname": "Segoe UI",
    "fontsize": "10",
    "penwidth": "1",
}


def output_path(name: str) -> str:
    return str(OUTPUT_DIR / name)


def icon(label: str, filename: str) -> Custom:
    return Custom(label, str(ICON_DIR / filename))


def legend(text: str) -> Node:
    return Node(
        text,
        shape="note",
        style="filled",
        fillcolor="#FFFFFF",
        color="#9E9E9E",
        fontname="Segoe UI",
        fontsize="9",
        fixedsize="false",
        labelloc="c",
        width="3.2",
        height="0.9",
        margin="0.16",
    )
