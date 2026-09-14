# Architecture diagram pack

These files describe the target Oracle Database Free to Microsoft Fabric environment. Nothing in this folder represents deployed Azure or Fabric resources.

## Views

| View | Purpose |
| --- | --- |
| `01-context` | Users, external services, Azure boundary, Oracle, and Fabric |
| `02-network-topology` | Tenant, subscription, region, VNet, subnets, private administration, DNS, and outbound access |
| `03-security-flows` | Allowed private flows, required outbound flows, and blocked Internet ingress |
| `04-data-flows` | Oracle snapshot and CDC path, Mirrored Database, SQL endpoint, and Lakehouse shortcut |

The SVG files are the primary documentation output. PNG files are included for presentations and PDF files for review packs.

## Source inventory

[`architecture-inventory.yaml`](architecture-inventory.yaml) is the source of truth for every node and connection. Values that depend on the target tenant remain `TBD`. The diagrams do not invent subscription IDs, regions, resource group names, CIDR ranges, listener ports, VM sizes, or Fabric capacity.

## Render locally

Requirements:

- Python 3.10 or later
- Graphviz with `dot.exe`
- packages from [`requirements.txt`](requirements.txt)

From the repository root:

```powershell
py -m pip install -r .\docs\architecture\requirements.txt
py .\docs\architecture\render.py
```

## Known assumptions

- The design is for a non-production PoC.
- Azure Bastion uses Premium private-only mode.
- Administration uses either point-to-site VPN or ExpressRoute.
- Controlled outbound access uses either NAT Gateway or Azure Firewall.
- The gateway uses HTTPS mode when the final policy permits it.

See the inventory for the full list of unresolved decisions.
