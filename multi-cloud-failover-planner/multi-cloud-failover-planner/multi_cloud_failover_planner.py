"""
Multi-Cloud Failover Planner (base version)

Given a set of cloud providers and the services running on them, this tool
builds a failover plan: when a provider (or region) goes down, each affected
service is moved to the best healthy provider that has enough spare capacity.

Run:  python multi_cloud_failover_planner.py
No third-party dependencies required (Python 3.8+).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Provider:
    name: str                 # e.g. "AWS"
    region: str               # e.g. "us-east-1"
    capacity: int             # total capacity units
    cost_per_unit: float      # relative cost, lower is cheaper
    latency_ms: int           # average latency to users
    healthy: bool = True
    used: int = 0             # capacity units currently in use

    @property
    def free(self) -> int:
        return self.capacity - self.used


@dataclass
class Service:
    name: str
    provider: str             # provider currently hosting it
    demand: int               # capacity units it needs
    priority: int = 1         # 1 = critical ... 3 = low


@dataclass
class FailoverAction:
    service: str
    source: str
    target: Optional[str]
    note: str = ""


@dataclass
class Planner:
    providers: Dict[str, Provider] = field(default_factory=dict)
    services: List[Service] = field(default_factory=list)

    # ---------- setup ----------
    def add_provider(self, p: Provider) -> None:
        self.providers[p.name] = p

    def add_service(self, s: Service) -> None:
        self.services.append(s)
        self.providers[s.provider].used += s.demand

    # ---------- health ----------
    def mark_down(self, provider_name: str) -> None:
        self.providers[provider_name].healthy = False

    # ---------- planning ----------
    def _score(self, p: Provider) -> float:
        """Lower score = better target (balances latency and cost)."""
        return p.latency_ms * 0.6 + p.cost_per_unit * 100 * 0.4

    def _best_target(self, service: Service) -> Optional[Provider]:
        candidates = [
            p for p in self.providers.values()
            if p.healthy and p.name != service.provider and p.free >= service.demand
        ]
        return min(candidates, key=self._score) if candidates else None

    def plan_failover(self) -> List[FailoverAction]:
        """Create a failover plan for every service on an unhealthy provider."""
        actions: List[FailoverAction] = []
        affected = [s for s in self.services if not self.providers[s.provider].healthy]

        # Critical services are placed first so they get capacity before others.
        for svc in sorted(affected, key=lambda s: s.priority):
            target = self._best_target(svc)
            if target is None:
                actions.append(FailoverAction(
                    svc.name, svc.provider, None,
                    "NO CAPACITY: manual intervention required"))
                continue
            target.used += svc.demand          # reserve capacity
            actions.append(FailoverAction(
                svc.name, svc.provider, target.name,
                f"moved to {target.name} ({target.region})"))
        return actions


def print_plan(actions: List[FailoverAction]) -> None:
    if not actions:
        print("All providers healthy. No failover needed.")
        return
    print(f"{'SERVICE':<18}{'FROM':<10}{'TO':<10}NOTE")
    print("-" * 62)
    for a in actions:
        print(f"{a.service:<18}{a.source:<10}{(a.target or '-'):<10}{a.note}")


def main() -> None:
    planner = Planner()

    planner.add_provider(Provider("AWS",   "us-east-1",   capacity=100, cost_per_unit=0.50, latency_ms=40))
    planner.add_provider(Provider("Azure", "eastus",      capacity=80,  cost_per_unit=0.55, latency_ms=45))
    planner.add_provider(Provider("GCP",   "us-central1", capacity=60,  cost_per_unit=0.45, latency_ms=55))

    planner.add_service(Service("payments-api",  "AWS", demand=30, priority=1))
    planner.add_service(Service("user-service",  "AWS", demand=25, priority=1))
    planner.add_service(Service("reporting",     "AWS", demand=20, priority=3))
    planner.add_service(Service("search",        "Azure", demand=20, priority=2))
    planner.add_service(Service("notifications", "GCP",   demand=15, priority=2))

    print("== Simulating outage on AWS ==\n")
    planner.mark_down("AWS")
    print_plan(planner.plan_failover())


if __name__ == "__main__":
    main()
