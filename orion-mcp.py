# orion-mcp.py
# A Model Context Protocol (MCP) server that provides a tool for running
# performance regression analysis using the cloud-bulldozer/orion library.

import os
import subprocess
import json
import mcp.types as types
from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("orion-mcp",log_level='INFO')

@mcp.tool()
def openshift_detailed_regression(
    version: str,
    data_source: str,
    lookback: str="15",
) -> list:
    """
    Runs a performance regression analysis against the OpenShift using Orion and provides a detailed report.

    Orion uses an EDivisive algorithm to analyze performance data from a specified
    configuration file to detect any performance regressions.

    Args:
        version: openshift version to look into.
        data_source: location of the data (OpenSearch URL).
        lookback: The number of days to look back for performance data. Defaults to 15 days.

    Returns:
        Returns a json of the regression analysis.
    """

    orion_configs = ["/orion/examples/trt-external-payload-cluster-density.yaml",
                     "/orion/examples/trt-external-payload-node-density.yaml",
                     "/orion/examples/trt-external-payload-node-density-cni.yaml",
                     "/orion/examples/trt-external-payload-crd-scale.yaml"]

    os.environ["ES_SERVER"] = data_source.strip()
    os.environ["version"] = version.strip()
    os.environ["es_metadata_index"] = "perf_scale_ci*"
    os.environ["es_benchmark_index"] = "ripsaw-kube-burner-*"
    # Store all the results in a list
    results = [] 
    # Prepare the command to run the orion tool.
    command = [
            "podman",
            "run",
            "--env-host",
            "orion",
            "orion",
            "cmd",
            "--lookback","{}d".format(lookback.strip()),
            "--hunter-analyze",
            "-o","json"
    ]
    try:
        for config in orion_configs:
            command.append("--config")
            command.append(config)
            # Execute the command as a subprocess
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                return [json.dumps(result.stdout)]

            data = {}
            data[config] = json.loads(result.stdout)
            results.append(data)

    except FileNotFoundError:
        err_msg = f"Error: 'orion' command not found. Please ensure the cloud-bulldozer/orion tool is installed and in your PATH. COMMAND: {' '.join(command)}"
        return err_msg
    except subprocess.CalledProcessError as e:
        error_message = f"Orion analysis failed with exit code {e.returncode}.\n"
        error_message += f"Stderr:\n{e.stderr}"
        error_message += f"Command: {' '.join(command)}\n"
        return error_message
    except json.JSONDecodeError:
        return "Error: Orion produced invalid JSON output. There might be an issue with the tool or the input data."
    except Exception as e:
        # Catch any other unexpected errors.
        return f"An unexpected error occurred: {str(e)}"
    return results

@mcp.tool()
def has_openshift_regressed(
    version: str,
    data_source: str,
    lookback: str="15",
) -> bool:
    """
    Runs a performance regression analysis against the OpenShift version using Orion and provides a high-level pass or fail.

    Orion uses an EDivisive algorithm to analyze performance data from a specified
    configuration file to detect any performance regressions.

    Args:
        version: openshift version to look into.
        data_source: location of the data (OpenSearch URL).
        lookback: The number of days to look back for performance data. Defaults to 15 days.

    Returns:
        Returns true if there is a regression and false if there is no regression found..
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
    command = [
            "podman",
            "run",
            "--env-host",
            "orion",
            "orion",
            "cmd",
            "--lookback","{}d".format(lookback.strip()),
            "--hunter-analyze"
    ]
    try:
        for config in orion_configs:
            command.append("--config")
            command.append(config)
            # Execute the command as a subprocess
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return True

    except FileNotFoundError:
        err_msg = f"Error: 'orion' command not found. Please ensure the cloud-bulldozer/orion tool is installed and in your PATH. COMMAND: {' '.join(command)}"
        return err_msg
    except subprocess.CalledProcessError as e:
        error_message = f"Orion analysis failed with exit code {e.returncode}.\n"
        error_message += f"Stderr:\n{e.stderr}"
        error_message += f"Command: {' '.join(command)}\n"
        return error_message
    except Exception as e:
        # Catch any other unexpected errors.
        return f"An unexpected error occurred: {str(e)}"
    return False