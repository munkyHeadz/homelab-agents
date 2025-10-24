"""
Docker MCP Server

Provides MCP tools for managing Docker containers and services:
- Container lifecycle management
- Image management
- Network management
- Volume management
- Docker Compose operations
- Container logs and stats
"""

import os
import docker
from typing import List, Dict, Any, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configuration
DOCKER_HOST = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
DOCKER_TLS_VERIFY = os.getenv("DOCKER_TLS_VERIFY", "0") == "1"

# Initialize MCP server
server = Server("docker-mcp")

# Initialize Docker client
docker_client = docker.DockerClient(base_url=DOCKER_HOST)


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Docker tools"""
    return [
        types.Tool(
            name="list_containers",
            description="List Docker containers",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Show all containers (default shows just running)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_container_details",
            description="Get detailed information about a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="start_container",
            description="Start a stopped container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="stop_container",
            description="Stop a running container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds to wait before killing",
                        "default": 10
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="restart_container",
            description="Restart a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="remove_container",
            description="Remove a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force removal of running container",
                        "default": False
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="get_container_logs",
            description="Get logs from a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines from the end (default: all)",
                        "default": 100
                    },
                    "since": {
                        "type": "string",
                        "description": "Show logs since timestamp (e.g., '2023-01-01T00:00:00')"
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="get_container_stats",
            description="Get resource usage statistics for a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name"
                    }
                },
                "required": ["container_id"]
            }
        ),
        types.Tool(
            name="list_images",
            description="List Docker images",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Show all images (including intermediates)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="pull_image",
            description="Pull a Docker image from registry",
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Image name (e.g., 'nginx:latest')"
                    }
                },
                "required": ["image"]
            }
        ),
        types.Tool(
            name="remove_image",
            description="Remove a Docker image",
            inputSchema={
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Image ID or name"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force removal",
                        "default": False
                    }
                },
                "required": ["image"]
            }
        ),
        types.Tool(
            name="list_networks",
            description="List Docker networks",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_volumes",
            description="List Docker volumes",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="prune_system",
            description="Remove unused Docker resources (containers, networks, images, volumes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Remove all unused images (not just dangling)",
                        "default": False
                    },
                    "volumes": {
                        "type": "boolean",
                        "description": "Prune volumes as well",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_system_info",
            description="Get Docker system information",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    try:
        if name == "list_containers":
            show_all = arguments.get("all", False)
            containers = docker_client.containers.list(all=show_all)

            if not containers:
                return [types.TextContent(
                    type="text",
                    text="No containers found" + (" (including stopped)" if show_all else " (running)")
                )]

            output = f"Found {len(containers)} containers:\\n\\n"
            for container in containers:
                status_emoji = "✅" if container.status == "running" else "⭕"
                output += f"{status_emoji} {container.name}\\n"
                output += f"   ID: {container.short_id}\\n"
                output += f"   Image: {container.image.tags[0] if container.image.tags else container.image.short_id}\\n"
                output += f"   Status: {container.status}\\n"
                output += f"   Ports: {container.ports}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_container_details":
            container = docker_client.containers.get(arguments["container_id"])
            stats = container.stats(stream=False)

            # Calculate CPU percentage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100.0

            # Calculate memory usage
            mem_usage = stats["memory_stats"]["usage"] / 1024 / 1024
            mem_limit = stats["memory_stats"]["limit"] / 1024 / 1024

            output = f"Container Details: {container.name}\\n" +\
                     f"ID: {container.id}\\n" +\
                     f"Image: {container.image.tags[0] if container.image.tags else 'unknown'}\\n" +\
                     f"Status: {container.status}\\n" +\
                     f"Created: {container.attrs['Created']}\\n" +\
                     f"CPU: {cpu_percent:.2f}%\\n" +\
                     f"Memory: {mem_usage:.1f} MB / {mem_limit:.1f} MB\\n" +\
                     f"Network: RX {stats['networks']['eth0']['rx_bytes'] / 1024 / 1024:.1f} MB, " +\
                     f"TX {stats['networks']['eth0']['tx_bytes'] / 1024 / 1024:.1f} MB"

            return [types.TextContent(type="text", text=output)]

        elif name == "start_container":
            container = docker_client.containers.get(arguments["container_id"])
            container.start()
            return [types.TextContent(
                type="text",
                text=f"✅ Container {container.name} started"
            )]

        elif name == "stop_container":
            container = docker_client.containers.get(arguments["container_id"])
            timeout = arguments.get("timeout", 10)
            container.stop(timeout=timeout)
            return [types.TextContent(
                type="text",
                text=f"✅ Container {container.name} stopped"
            )]

        elif name == "restart_container":
            container = docker_client.containers.get(arguments["container_id"])
            container.restart()
            return [types.TextContent(
                type="text",
                text=f"✅ Container {container.name} restarted"
            )]

        elif name == "remove_container":
            container = docker_client.containers.get(arguments["container_id"])
            force = arguments.get("force", False)
            container.remove(force=force)
            return [types.TextContent(
                type="text",
                text=f"✅ Container {arguments['container_id']} removed"
            )]

        elif name == "get_container_logs":
            container = docker_client.containers.get(arguments["container_id"])
            tail = arguments.get("tail", 100)
            since = arguments.get("since")

            logs_kwargs = {"tail": tail}
            if since:
                logs_kwargs["since"] = since

            logs = container.logs(**logs_kwargs).decode("utf-8")

            return [types.TextContent(
                type="text",
                text=f"Logs for {container.name} (last {tail} lines):\\n\\n{logs}"
            )]

        elif name == "get_container_stats":
            container = docker_client.containers.get(arguments["container_id"])
            stats = container.stats(stream=False)

            # Calculate metrics
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"]) * 100.0

            mem_usage = stats["memory_stats"]["usage"] / 1024 / 1024
            mem_limit = stats["memory_stats"]["limit"] / 1024 / 1024

            output = f"Resource Stats for {container.name}:\\n" +\
                     f"CPU: {cpu_percent:.2f}%\\n" +\
                     f"Memory: {mem_usage:.1f} MB / {mem_limit:.1f} MB ({mem_usage/mem_limit*100:.1f}%)\\n" +\
                     f"Network RX: {stats['networks']['eth0']['rx_bytes'] / 1024 / 1024:.1f} MB\\n" +\
                     f"Network TX: {stats['networks']['eth0']['tx_bytes'] / 1024 / 1024:.1f} MB"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_images":
            show_all = arguments.get("all", False)
            images = docker_client.images.list(all=show_all)

            if not images:
                return [types.TextContent(type="text", text="No images found")]

            output = f"Found {len(images)} images:\\n\\n"
            for image in images:
                tags = image.tags if image.tags else ["<none>"]
                output += f"📦 {tags[0]}\\n"
                output += f"   ID: {image.short_id}\\n"
                output += f"   Size: {image.attrs['Size'] / 1024 / 1024:.1f} MB\\n"
                output += f"   Created: {image.attrs['Created']}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "pull_image":
            image_name = arguments["image"]
            image = docker_client.images.pull(image_name)
            return [types.TextContent(
                type="text",
                text=f"✅ Image {image_name} pulled successfully"
            )]

        elif name == "remove_image":
            image_name = arguments["image"]
            force = arguments.get("force", False)
            docker_client.images.remove(image_name, force=force)
            return [types.TextContent(
                type="text",
                text=f"✅ Image {image_name} removed"
            )]

        elif name == "list_networks":
            networks = docker_client.networks.list()

            output = f"Found {len(networks)} networks:\\n\\n"
            for network in networks:
                output += f"🌐 {network.name}\\n"
                output += f"   ID: {network.short_id}\\n"
                output += f"   Driver: {network.attrs['Driver']}\\n"
                output += f"   Scope: {network.attrs['Scope']}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "list_volumes":
            volumes = docker_client.volumes.list()

            output = f"Found {len(volumes)} volumes:\\n\\n"
            for volume in volumes:
                output += f"💾 {volume.name}\\n"
                output += f"   Driver: {volume.attrs['Driver']}\\n"
                output += f"   Mountpoint: {volume.attrs['Mountpoint']}\\n\\n"

            return [types.TextContent(type="text", text=output)]

        elif name == "prune_system":
            prune_all = arguments.get("all", False)
            prune_volumes = arguments.get("volumes", False)

            # Prune containers
            containers_pruned = docker_client.containers.prune()

            # Prune images
            images_pruned = docker_client.images.prune(filters={"dangling": not prune_all})

            # Prune networks
            networks_pruned = docker_client.networks.prune()

            # Prune volumes if requested
            volumes_pruned = {"VolumesDeleted": [], "SpaceReclaimed": 0}
            if prune_volumes:
                volumes_pruned = docker_client.volumes.prune()

            total_space = (
                containers_pruned.get("SpaceReclaimed", 0) +
                images_pruned.get("SpaceReclaimed", 0) +
                volumes_pruned.get("SpaceReclaimed", 0)
            ) / 1024 / 1024 / 1024

            output = f"System Prune Complete:\\n" +\
                     f"Containers removed: {len(containers_pruned.get('ContainersDeleted', []))}\\n" +\
                     f"Images removed: {len(images_pruned.get('ImagesDeleted', []))}\\n" +\
                     f"Networks removed: {len(networks_pruned.get('NetworksDeleted', []))}\\n" +\
                     f"Volumes removed: {len(volumes_pruned.get('VolumesDeleted', []))}\\n" +\
                     f"Space reclaimed: {total_space:.2f} GB"

            return [types.TextContent(type="text", text=output)]

        elif name == "get_system_info":
            info = docker_client.info()

            output = f"Docker System Information:\\n" +\
                     f"Containers: {info['Containers']} (Running: {info['ContainersRunning']})\\n" +\
                     f"Images: {info['Images']}\\n" +\
                     f"Server Version: {info['ServerVersion']}\\n" +\
                     f"Storage Driver: {info['Driver']}\\n" +\
                     f"Operating System: {info['OperatingSystem']}\\n" +\
                     f"CPUs: {info['NCPU']}\\n" +\
                     f"Total Memory: {info['MemTotal'] / 1024 / 1024 / 1024:.1f} GB"

            return [types.TextContent(type="text", text=output)]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="docker",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
