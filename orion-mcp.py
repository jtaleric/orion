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

def run_orion(
    lookback: str,
    config : str,
    data_source: str,
    version: str,
) -> subprocess.CompletedProcess :
    """
    Executes Orion to analyze performance data for regressions.

    Args:
        lookback (str): Days to look back for performance data. 
        config (str): Path to the Orion configuration file to use for analysis.
        data_source (str):  Location of the data (OpenSearch URL) to analyze. 
        version (str): Version to analyze. 

    Returns:
        subprocess.CompletedProcess: The result of the Orion command execution, including stdout and stderr. 
    """

    command = [
            "podman",
            "run",
            "--env-host",
            "orion",
            "orion",
            "cmd",
            "--lookback","{}d".format(lookback.strip()),
            "--hunter-analyze",
            "--config", config,
            "-o","json"
    ]

    os.environ["ES_SERVER"] = data_source.strip()
    os.environ["version"] = version.strip()
    os.environ["es_metadata_index"] = "perf_scale_ci*"
    os.environ["es_benchmark_index"] = "ripsaw-kube-burner-*"
    try:
        # Execute the command as a subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
            
        if result.returncode != 0:
            return result 

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
    return result

def convert_results_to_csv(results : list) -> str:
    """
    Converts the results of the Orion analysis into a CSV format.

    Args:
        results (list): The list of results from the Orion analysis.

    Returns:
        str: A string containing the CSV representation of the results.
    """
    csv_lines = []
    for result in results:
        for config, data in result.items():
            if not data:
                continue
            for metric, values in data.items():
                if metric == "timestamp":
                    continue
                csv_lines.append(f"{config},{metric},{','.join(map(str, values['value']))}")
    return "\n".join(csv_lines)

def summarize_result(
    result: subprocess.CalledProcessError 
) -> dict :
    """
    Summarizes the Orion result into a dictionary.

    Args:
        result (str): The JSON output from the Orion command.
        config (str): The configuration file used for the Orion analysis.

    Returns:
        dict: A dictionary containing the summary of the Orion analysis.
    """
    summary = {}
    try:
        data = json.loads(result.stdout)
        if len(data) == 0:
            return {}
        for run in data :
            for metric_name, metric_data in run["metrics"].items():
                summary["timestamp"] = run["timestamp"]
                if metric_name not in summary:
                    summary[metric_name] = {}
                    summary[metric_name] = {
                        "value": [ metric_data["value"] ],
                    }
                else :
                    summary[metric_name]["value"].append(metric_data["value"]) 
    except json.JSONDecodeError:
        return {}
    return summary

@mcp.tool()
def openshift_detailed_regression(
    version: str,
    data_source: str,
    lookback: str="15",
) -> str:
    """
    Runs a performance regression analysis against the OpenShift using Orion and provides a detailed report.

    Orion uses an EDivisive algorithm to analyze performance data from a specified
    configuration file to detect any performance regressions.

    Args:
        version: openshift version to look into.
        data_source: location of the data (OpenSearch URL).
        lookback: The number of days to look back for performance data. Defaults to 15 days.

    Returns:
        Returns a string of csv values showing metrics captured for regression analysis.
    """
    orion_configs = ["/orion/examples/trt-external-payload-cluster-density.yaml",
                     "/orion/examples/trt-external-payload-node-density.yaml",
                     "/orion/examples/trt-external-payload-node-density-cni.yaml",
                     "/orion/examples/trt-external-payload-crd-scale.yaml"]

    # Store all the results in a list
    results = [] 
    # Prepare the command to run the orion tool.
    for config in orion_configs:
        data = {}
        result = run_orion(
            lookback=lookback.strip(),
            config=config,
            data_source=data_source.strip(),
            version=version.strip()
        )
        if result.returncode != 0:
            return convert_results_to_csv(summarize_result(result))

        data[config] = {}
        data[config] = summarize_result(result)
        results.append(data)
    return convert_results_to_csv(results)

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

    for config in orion_configs:
        # Execute the command as a subprocess
        result = run_orion(
            lookback=lookback.strip(),
            config=config,
            data_source=data_source.strip(),
            version=version.strip()
        )
        if result.returncode != 0:
            return True
    return False