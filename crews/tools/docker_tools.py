"""Docker management and monitoring tools for homelab agents."""

from datetime import datetime
from typing import Optional

import docker
import humanize
from crewai.tools import tool

from crews.approval import get_approval_manager


def get_docker_client():
    """Get Docker client instance."""
    try:
        return docker.DockerClient(base_url="unix://var/run/docker.sock")
    except Exception as e:
        raise Exception(f"Failed to connect to Docker: {str(e)}")


@tool("List Docker Images")
def list_docker_images(show_all: bool = False) -> str:
    """
    List Docker images with size and usage information.

    Args:
        show_all: If True, include intermediate images. Default False.

    Returns:
        String with image inventory, sizes, and dangling image detection

    Use Cases:
        - Identify large images consuming disk space
        - Detect dangling/unused images
        - Track image versions and tags
        - Plan image cleanup operations
    """
    try:
        client = get_docker_client()
        images = client.images.list(all=show_all)

        if not images:
            return "No Docker images found"

        # Calculate total size
        total_size = sum(img.attrs["Size"] for img in images)

        # Categorize images
        tagged_images = []
        dangling_images = []

        for img in images:
            size = img.attrs["Size"]
            size_human = humanize.naturalsize(size)
            created = datetime.fromtimestamp(img.attrs["Created"]).strftime(
                "%Y-%m-%d %H:%M"
            )

            # Check if dangling (no tags)
            tags = img.tags
            if not tags or tags == ["<none>:<none>"]:
                dangling_images.append(
                    f"  {img.short_id}: {size_human} (created {created})"
                )
            else:
                # Get first tag for display
                tag = tags[0] if tags else img.short_id
                tagged_images.append(f"  {tag}: {size_human} (created {created})")

        result = [
            "=== Docker Images Summary ===",
            f"Total images: {len(images)}",
            f"Total size: {humanize.naturalsize(total_size)}",
            f"Tagged images: {len(tagged_images)}",
            f"Dangling images: {len(dangling_images)}",
            "",
        ]

        if tagged_images:
            result.append("Tagged Images:")
            result.extend(tagged_images[:20])  # Limit to 20 for readability
            if len(tagged_images) > 20:
                result.append(f"  ... and {len(tagged_images) - 20} more")
            result.append("")

        if dangling_images:
            result.append("⚠️ Dangling Images (no tags):")
            result.extend(dangling_images)
            result.append("")
            result.append("💡 Tip: Use prune_docker_images to clean up dangling images")

        return "\n".join(result)

    except Exception as e:
        return f"✗ Error listing Docker images: {str(e)}"


@tool("Prune Docker Images")
def prune_docker_images(remove_dangling_only: bool = True) -> str:
    """
    Clean up unused Docker images to free disk space.

    Args:
        remove_dangling_only: If True, only remove dangling images (no tags).
                             If False, remove all unused images (CAUTION).

    Returns:
        String with cleanup results and space reclaimed

    Use Cases:
        - Free up disk space from old/unused images
        - Regular maintenance to prevent disk exhaustion
        - Clean up after deployments
        - Remove build artifacts

    Safety:
        - remove_dangling_only=True (default): Safe, only removes untagged images
        - remove_dangling_only=False: Removes ALL unused images (use with caution)
    """
    try:
        client = get_docker_client()

        # Get images before pruning for comparison
        images_before = len(client.images.list())

        if remove_dangling_only:
            # Safe mode: only remove dangling images
            result = client.images.prune(filters={"dangling": True})
            mode = "dangling images only"
        else:
            # Aggressive mode: remove all unused images
            result = client.images.prune(filters={"dangling": False})
            mode = "all unused images"

        images_after = len(client.images.list())
        images_removed = images_before - images_after
        space_reclaimed = result.get("SpaceReclaimed", 0)

        deleted_images = result.get("ImagesDeleted", [])

        output = [
            "=== Docker Image Cleanup Complete ===",
            f"Mode: {mode}",
            f"Images removed: {images_removed}",
            f"Space reclaimed: {humanize.naturalsize(space_reclaimed)}",
            "",
        ]

        if deleted_images:
            output.append("Deleted images:")
            for img in deleted_images[:10]:  # Show first 10
                deleted = img.get("Deleted", img.get("Untagged", "unknown"))
                output.append(f"  {deleted}")
            if len(deleted_images) > 10:
                output.append(f"  ... and {len(deleted_images) - 10} more")

        if space_reclaimed > 0:
            output.append("")
            output.append("✓ Cleanup successful - disk space freed")
        elif images_removed == 0:
            output.append("✓ No unused images to remove - system is clean")

        return "\n".join(output)

    except Exception as e:
        return f"✗ Error pruning Docker images: {str(e)}"


@tool("Inspect Docker Network")
def inspect_docker_network(network_name: Optional[str] = None) -> str:
    """
    Inspect Docker networks and connected containers.

    Args:
        network_name: Optional specific network to inspect.
                     If None, lists all networks with container counts.

    Returns:
        String with network configuration and connected containers

    Use Cases:
        - Troubleshoot container connectivity issues
        - Verify network isolation
        - Check which containers can communicate
        - Diagnose network-related incidents
    """
    try:
        client = get_docker_client()

        if network_name:
            # Inspect specific network
            try:
                network = client.networks.get(network_name)

                # Get network details
                driver = network.attrs.get("Driver", "unknown")
                scope = network.attrs.get("Scope", "unknown")
                internal = network.attrs.get("Internal", False)

                # Get connected containers
                containers = network.attrs.get("Containers", {})

                output = [
                    f"=== Network: {network_name} ===",
                    f"Driver: {driver}",
                    f"Scope: {scope}",
                    f"Internal: {internal}",
                    f"Connected containers: {len(containers)}",
                    "",
                ]

                if containers:
                    output.append("Containers on this network:")
                    for container_id, container_info in containers.items():
                        name = container_info.get("Name", "unknown")
                        ipv4 = container_info.get("IPv4Address", "N/A")
                        output.append(f"  • {name} ({ipv4})")
                else:
                    output.append("⚠️ No containers connected to this network")

                # Check for network configuration
                ipam = network.attrs.get("IPAM", {})
                config = ipam.get("Config", [])
                if config:
                    output.append("")
                    output.append("Network Configuration:")
                    for cfg in config:
                        subnet = cfg.get("Subnet", "N/A")
                        gateway = cfg.get("Gateway", "N/A")
                        output.append(f"  Subnet: {subnet}, Gateway: {gateway}")

                return "\n".join(output)

            except docker.errors.NotFound:
                return f"✗ Network '{network_name}' not found"
        else:
            # List all networks
            networks = client.networks.list()

            output = ["=== Docker Networks ===", f"Total networks: {len(networks)}", ""]

            for net in networks:
                name = net.name
                driver = net.attrs.get("Driver", "unknown")
                container_count = len(net.attrs.get("Containers", {}))
                scope = net.attrs.get("Scope", "unknown")

                output.append(
                    f"• {name} ({driver}, {scope}): {container_count} containers"
                )

            output.append("")
            output.append(
                "💡 Tip: Use inspect_docker_network('network_name') for details"
            )

            return "\n".join(output)

    except Exception as e:
        return f"✗ Error inspecting Docker network: {str(e)}"


@tool("Check Docker Volumes")
def check_docker_volumes(show_usage: bool = True) -> str:
    """
    Check Docker volumes and detect orphaned volumes.

    Args:
        show_usage: If True, attempts to show which containers use each volume

    Returns:
        String with volume inventory and orphaned volume detection

    Use Cases:
        - Detect orphaned volumes wasting disk space
        - Verify data persistence configuration
        - Track volume growth
        - Plan volume cleanup
    """
    try:
        client = get_docker_client()
        volumes = client.volumes.list()

        if not volumes:
            return "No Docker volumes found"

        # Get all containers (running and stopped) to check volume usage
        containers = client.containers.list(all=True)

        # Map volumes to containers
        volume_usage = {}
        for container in containers:
            mounts = container.attrs.get("Mounts", [])
            for mount in mounts:
                if mount.get("Type") == "volume":
                    vol_name = mount.get("Name")
                    if vol_name:
                        if vol_name not in volume_usage:
                            volume_usage[vol_name] = []
                        volume_usage[vol_name].append(container.name)

        # Categorize volumes
        used_volumes = []
        orphaned_volumes = []

        for vol in volumes:
            name = vol.name
            # Try to get size (may not be available on all Docker versions)
            try:
                size = vol.attrs.get("UsageData", {}).get("Size", 0)
                size_str = humanize.naturalsize(size) if size else "unknown"
            except:
                size_str = "unknown"

            if name in volume_usage:
                containers_using = volume_usage[name]
                used_volumes.append(
                    f"  • {name}: {size_str} (used by {', '.join(containers_using)})"
                )
            else:
                orphaned_volumes.append(f"  • {name}: {size_str}")

        output = [
            "=== Docker Volumes ===",
            f"Total volumes: {len(volumes)}",
            f"Used volumes: {len(used_volumes)}",
            f"Orphaned volumes: {len(orphaned_volumes)}",
            "",
        ]

        if used_volumes:
            output.append("Used Volumes:")
            output.extend(used_volumes[:15])  # Limit for readability
            if len(used_volumes) > 15:
                output.append(f"  ... and {len(used_volumes) - 15} more")
            output.append("")

        if orphaned_volumes:
            output.append("⚠️ Orphaned Volumes (not used by any container):")
            output.extend(orphaned_volumes)
            output.append("")
            output.append(
                "💡 Consider removing orphaned volumes with 'docker volume prune'"
            )
            output.append("   (Manual operation - requires user approval)")

        return "\n".join(output)

    except Exception as e:
        return f"✗ Error checking Docker volumes: {str(e)}"


@tool("Get Container Resource Usage")
def get_container_resource_usage(container_name: Optional[str] = None) -> str:
    """
    Get real-time resource usage for Docker containers.

    Args:
        container_name: Optional specific container. If None, shows all running containers.

    Returns:
        String with CPU, memory, network, and block I/O usage

    Use Cases:
        - Identify resource-hungry containers
        - Detect memory leaks or CPU spikes
        - Capacity planning
        - Performance troubleshooting
        - Complement Prometheus metrics with instant snapshot
    """
    try:
        client = get_docker_client()

        if container_name:
            # Get specific container stats
            try:
                container = client.containers.get(container_name)
                if container.status != "running":
                    return f"Container '{container_name}' is not running (status: {container.status})"

                # Get stats (stream=False for single snapshot)
                stats = container.stats(stream=False)

                output = [f"=== Resource Usage: {container_name} ==="]
                output.extend(_format_container_stats(container_name, stats))

                return "\n".join(output)

            except docker.errors.NotFound:
                return f"✗ Container '{container_name}' not found"
        else:
            # Get stats for all running containers
            containers = client.containers.list()  # Only running containers

            if not containers:
                return "No running containers found"

            output = [
                "=== Container Resource Usage (All Running) ===",
                f"Total running containers: {len(containers)}",
                "",
            ]

            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    output.append(f"Container: {container.name}")
                    output.extend(_format_container_stats(container.name, stats))
                    output.append("")
                except Exception as e:
                    output.append(f"Container: {container.name} - Error: {str(e)}")
                    output.append("")

            return "\n".join(output)

    except Exception as e:
        return f"✗ Error getting container resource usage: {str(e)}"


def _format_container_stats(container_name: str, stats: dict) -> list:
    """Helper function to format container stats."""
    output = []

    try:
        # CPU usage calculation
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        cpu_count = stats["cpu_stats"].get("online_cpus", 1)

        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
        else:
            cpu_percent = 0.0

        output.append(f"  CPU: {cpu_percent:.2f}%")

        # Memory usage
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 0)

        if mem_limit > 0:
            mem_percent = (mem_usage / mem_limit) * 100.0
            output.append(
                f"  Memory: {humanize.naturalsize(mem_usage)} / {humanize.naturalsize(mem_limit)} ({mem_percent:.1f}%)"
            )
        else:
            output.append(f"  Memory: {humanize.naturalsize(mem_usage)}")

        # Network I/O
        networks = stats.get("networks", {})
        if networks:
            total_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
            total_tx = sum(net.get("tx_bytes", 0) for net in networks.values())
            output.append(
                f"  Network: RX {humanize.naturalsize(total_rx)}, TX {humanize.naturalsize(total_tx)}"
            )

        # Block I/O
        blkio_stats = stats.get("blkio_stats", {})
        io_service_bytes = blkio_stats.get("io_service_bytes_recursive", [])
        if io_service_bytes:
            read_bytes = sum(
                item["value"] for item in io_service_bytes if item["op"] == "read"
            )
            write_bytes = sum(
                item["value"] for item in io_service_bytes if item["op"] == "write"
            )
            output.append(
                f"  Block I/O: Read {humanize.naturalsize(read_bytes)}, Write {humanize.naturalsize(write_bytes)}"
            )

    except KeyError as e:
        output.append(f"  ⚠️ Could not parse stats: missing field {e}")
    except Exception as e:
        output.append(f"  ⚠️ Error formatting stats: {str(e)}")

    return output


@tool("Check Docker System Health")
def check_docker_system_health() -> str:
    """
    Check overall Docker daemon health and system resource usage.

    Returns:
        String with Docker daemon status, disk usage, and health warnings

    Use Cases:
        - Monitor Docker daemon health
        - Detect disk space issues before they cause problems
        - Verify Docker is operating normally
        - Regular health checks
    """
    try:
        client = get_docker_client()

        # Get Docker info
        info = client.info()

        # Get version
        version = client.version()

        # Get disk usage
        df = client.df()

        output = [
            "=== Docker System Health ===",
            f"Docker Version: {version.get('Version', 'unknown')}",
            f"API Version: {version.get('ApiVersion', 'unknown')}",
            f"OS: {info.get('OperatingSystem', 'unknown')}",
            f"Architecture: {info.get('Architecture', 'unknown')}",
            "",
        ]

        # Container stats
        containers_total = info.get("Containers", 0)
        containers_running = info.get("ContainersRunning", 0)
        containers_paused = info.get("ContainersPaused", 0)
        containers_stopped = info.get("ContainersStopped", 0)

        output.append("Container Summary:")
        output.append(f"  Total: {containers_total}")
        output.append(f"  Running: {containers_running}")
        output.append(f"  Paused: {containers_paused}")
        output.append(f"  Stopped: {containers_stopped}")
        output.append("")

        # Images
        images_count = info.get("Images", 0)
        output.append(f"Images: {images_count}")
        output.append("")

        # Storage driver
        storage_driver = info.get("Driver", "unknown")
        output.append(f"Storage Driver: {storage_driver}")

        # Disk usage breakdown
        output.append("")
        output.append("Disk Usage Breakdown:")

        # Images
        images_size = df.get("Images", [])
        if images_size:
            total_img_size = sum(img.get("Size", 0) for img in images_size)
            active_img_size = sum(
                img.get("Size", 0)
                for img in images_size
                if not img.get("Containers", 0) == -1
            )
            reclaimable = total_img_size - active_img_size
            output.append(
                f"  Images: {humanize.naturalsize(total_img_size)} "
                f"(reclaimable: {humanize.naturalsize(reclaimable)})"
            )

        # Containers
        containers_usage = df.get("Containers", [])
        if containers_usage:
            total_cont_size = sum(c.get("SizeRw", 0) for c in containers_usage)
            output.append(f"  Containers: {humanize.naturalsize(total_cont_size)}")

        # Volumes
        volumes_usage = df.get("Volumes", [])
        if volumes_usage:
            total_vol_size = sum(
                v.get("UsageData", {}).get("Size", 0) for v in volumes_usage
            )
            output.append(f"  Volumes: {humanize.naturalsize(total_vol_size)}")

        # Build cache
        build_cache = df.get("BuildCache", [])
        if build_cache:
            total_cache_size = sum(b.get("Size", 0) for b in build_cache)
            reclaimable_cache = sum(
                b.get("Size", 0) for b in build_cache if b.get("Shared", False) == False
            )
            output.append(
                f"  Build Cache: {humanize.naturalsize(total_cache_size)} "
                f"(reclaimable: {humanize.naturalsize(reclaimable_cache)})"
            )

        # Health warnings
        output.append("")
        warnings = []

        # Check if any images are reclaimable
        if images_size:
            if reclaimable > 1024 * 1024 * 1024:  # > 1GB
                warnings.append(
                    f"⚠️ {humanize.naturalsize(reclaimable)} of image space can be reclaimed"
                )

        # Check for stopped containers
        if containers_stopped > 5:
            warnings.append(
                f"⚠️ {containers_stopped} stopped containers (consider cleanup)"
            )

        # Check for paused containers (unusual)
        if containers_paused > 0:
            warnings.append(f"⚠️ {containers_paused} paused containers detected")

        if warnings:
            output.append("Health Warnings:")
            output.extend([f"  {w}" for w in warnings])
            output.append("")
            output.append(
                "💡 Use prune_docker_images and docker system prune for cleanup"
            )
        else:
            output.append("✓ Docker system health is good - no warnings")

        return "\n".join(output)

    except Exception as e:
        return f"✗ Error checking Docker system health: {str(e)}"


@tool("Update Docker Container Resources")
def update_docker_resources(
    container: str,
    cpu_limit: str = None,
    memory_limit: str = None,
    dry_run: bool = False,
) -> str:
    """
    Update Docker container resource limits.

    Args:
        container: Container name or ID
        cpu_limit: CPU limit (e.g., "2.0" for 2 cores, "0.5" for half a core)
        memory_limit: Memory limit (e.g., "2g" for 2GB, "512m" for 512MB)
        dry_run: If True, only show what would be changed

    Returns:
        Status message with changes applied

    Safety:
        - Validates container exists
        - Supports dry-run mode
        - Requires approval for production containers

    Use cases:
        - Limit runaway container resource usage
        - Temporarily boost resources for intensive task
        - Enforce resource quotas
    """
    try:
        import docker

        client = docker.from_env()

        try:
            container_obj = client.containers.get(container)
        except docker.errors.NotFound:
            return f"❌ Container '{container}' not found"

        container_name = container_obj.name

        changes = []
        update_params = {}

        if cpu_limit is not None:
            current_cpu = container_obj.attrs["HostConfig"].get("NanoCpus", 0) / 1e9
            changes.append(f"CPU: {current_cpu} → {cpu_limit} cores")
            # Docker uses nanocpus (1 CPU = 1e9 nanocpus)
            update_params["cpu_quota"] = int(float(cpu_limit) * 100000)
            update_params["cpu_period"] = 100000

        if memory_limit is not None:
            current_mem = container_obj.attrs["HostConfig"].get("Memory", 0)
            current_mem_str = (
                f"{current_mem / (1024**3):.1f}g" if current_mem > 0 else "unlimited"
            )
            changes.append(f"Memory: {current_mem_str} → {memory_limit}")
            update_params["mem_limit"] = memory_limit

        if not changes:
            return f"ℹ️ No changes specified for container '{container_name}'"

        if dry_run:
            output = [f"🔍 DRY-RUN: Would update container '{container_name}'\n"]
            output.append("**Proposed Changes**:")
            for change in changes:
                output.append(f"  • {change}")
            return "\n".join(output)

        # Check if critical container and request approval
        approval_manager = get_approval_manager()
        if approval_manager.is_critical_service("docker", container_name):
            details = f"Container: {container_name}\nChanges:\n" + "\n".join(
                f"  • {c}" for c in changes
            )

            approval_result = approval_manager.send_approval_request(
                action=f"Update resources for container '{container_name}'",
                details=details,
                severity="warning",
            )

            if not approval_result["approved"]:
                return f"❌ Action rejected: {approval_result['reason']}\nChanges NOT applied to {container_name}"

        # Apply changes
        container_obj.update(**update_params)

        output = [f"✅ Successfully updated container '{container_name}'\n"]
        output.append("**Changes Applied**:")
        for change in changes:
            output.append(f"  • {change}")
        output.append("\n⚠️ **Note**: Container continues running with new limits")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error updating container resources: {str(e)}"
