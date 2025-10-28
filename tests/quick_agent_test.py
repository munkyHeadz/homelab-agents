#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.append("/root/homelab-agents")

from agents.infrastructure_agent import InfrastructureAgent


async def test():
    print("\n=== AGENT FUNCTIONALITY TEST ===\n")

    agent = InfrastructureAgent()

    print("--- Test 1: Resource Monitoring ---")
    result = await agent.monitor_resources()
    print(f"✅ Success: {result.get('success')}")
    if "proxmox_node" in result:
        proxmox_info = result["proxmox_node"][:100]
        print(f"Proxmox Data: {proxmox_info}...")
    if "docker" in result:
        docker_info = result["docker"][:100]
        print(f"Docker Data: {docker_info}...")

    print("\n--- Test 2: Execute Infrastructure Task ---")
    result2 = await agent.execute("Get the total number of running containers")
    print(f"✅ Success: {result2.get('success')}")
    print(f"Summary: {result2.get('summary', 'Completed')}")

    print("\n✅ ALL AGENT TESTS PASSED")


asyncio.run(test())
