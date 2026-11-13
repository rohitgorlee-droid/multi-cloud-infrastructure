# Multi-Cloud Failover Planner

Simple base project: builds a failover plan when a cloud provider goes down.
Critical services are placed first on the healthy provider with enough spare
capacity and the best latency/cost score.

## Run
    python multi_cloud_failover_planner.py

Requires Python 3.8+. No external dependencies.
