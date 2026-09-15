# Architecture diagram pack

These files describe the deployed Oracle to Fabric Demo environment, validated on September 15, 2026.

## Views

| View | Purpose |
| --- | --- |
| `01-context` | Administrator, Bastion Developer, private Azure workloads, outbound NAT, Oracle, and Fabric |
| `02-network-topology` | Tenant, subscription, Central US VNet, Demo subnets, DNS, and outbound access |
| `03-security-flows` | Allowed private flows, required outbound flows, and blocked Internet ingress |
| `04-data-flows` | Oracle snapshot and CDC path, Mirrored Database, SQL endpoint, and Lakehouse shortcut |

The SVG files are the primary documentation output. PNG files are included for presentations and PDF files for review packs.

## Source inventory

[`architecture-inventory.yaml`](architecture-inventory.yaml) is the source of truth for every node and connection. Tenant and subscription identifiers are deliberately not stored.

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

## Deployed notes

- The environment is a non-production Demo.
- Azure Bastion uses the free Developer SKU.
- No VPN Gateway or `AzureBastionSubnet` is deployed.
- Neither VM has a public IP.
- One outbound-only public IP is attached to NAT Gateway because the Fabric gateway requires egress.
- `DemoLakehouse` is schema-enabled and exposes the five shortcuts under `DEMO_DW`.
- The gateway uses its bundled managed ODP.NET driver for Oracle mirroring.
