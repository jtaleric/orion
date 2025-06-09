# orion-mcp.py
# A Model Context Protocol (MCP) server that provides a tool for running
# performance regression analysis using the cloud-bulldozer/orion library.

import os
import subprocess
import json
import mcp.types as types
from typing import Literal, Optional

from fastmcp import FastMCP, Context

mcp = FastMCP("orion-mcp", title="Orion Performance Regression Analyzer",log_level='INFO')


@mcp.tool()
def has_openshift_regressed(
    version: str,
    data_source: str,
    ctx: Context,
    lookback: str="15",
) -> bool:
    """
    Runs a performance regression analysis against the OpenShift Product using Orion.

    Orion uses an EDivisive algorithm to analyze performance data from a specified
    configuration file to detect any performance regressions.

    Args:
        version: openshift version to look into.
        data_source: location of the data (OpenSearch URL).
        lookback: The number of days to look back for performance data. Defaults to 15 days.

    Returns:
        True if OpenShift has regressed for the given version and lookback
        False if OpenShift has not seen a regression for the given version and lookback
    """

    orion_configs = ["/orion/examples/trt-external-payload-cluster-density.yaml",
                     "/orion/examples/trt-external-payload-node-density.yaml",
                     "/orion/examples/trt-external-payload-node-density-cni.yaml",
                     "/orion/examples/trt-external-payload-crd-scale.yaml"]

    os.environ["ES_SERVER"] = data_source.strip()
    os.environ["version"] = version.strip()
    os.environ["es_metadata_index"] = "perf_scale_ci*"
    os.environ["es_benchmark_index"] = "ripsaw-kube-burner-*"
    # Prepare the command to run the orion tool.
    # version=4.19* es_metadata_index=perf_scale_ci* es_benchmark_index=ripsaw-kube-burner-* orion cmd --config examples/trt-external-payload-cluster-density.yaml --hunter-analyze --node-count true --debug
    command = [
            "podman",
            "run",
            "--env-host",
            "orion",
            "orion",
            "cmd",
            "--config", "/orion/examples/trt-external-payload-cluster-density.yaml", 
            "--lookback","{}d".format(lookback.strip()),
            "--hunter-analyze"
    ]

    try:
        # Execute the command as a subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )

        # Check if the command was successful
        if result.returncode != 0:
            return True
        
        return False

    except FileNotFoundError:
        err_msg = f"Error: 'orion' command not found. Please ensure the cloud-bulldozer/orion tool is installed and in your PATH. COMMAND: {' '.join(command)}"
        return err_msg
    except subprocess.CalledProcessError as e:
        error_message = f"Orion analysis failed with exit code {e.returncode}.\n"
        error_message += f"Stderr:\n{e.stderr}"
        error_message += f"Command: {' '.join(command)}\n"
        return error_message
    # old will remove soon if we don't process the json output
    except json.JSONDecodeError:
        return "Error: Orion produced invalid JSON output. There might be an issue with the tool or the input data."
    except Exception as e:
        # Catch any other unexpected errors.
        return f"An unexpected error occurred: {str(e)}"
