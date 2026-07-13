from dataclasses import dataclass, field


@dataclass(slots=True)
class DashboardModel:

    production: float = 0.0
    packaging: float = 0.0
    shipment: float = 0.0
    critical: int = 0

    recent_production: list = field(default_factory=list)
    recent_shipment: list = field(default_factory=list)
    critical_stock: list = field(default_factory=list)
