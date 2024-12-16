"""
This script processes mitmproxy flow files, filters them based on prefixes, and logs requests to domains specified as excluded.
It will:
- Identify flow files associated with given prefix.
- Parse each flow file and iterate through the recorded HTTP flows.
- For each request, if its host matches an excluded domain, log a warning.
"""

import argparse
import logging
import os
import sys

from mitmproxy import io
from mitmproxy.exceptions import FlowReadException


def setup_logging(log_to_file: bool, log_file: str) -> logging.Logger:
    """
    Set up logging configuration.

    Parameters
    ----------
    log_to_file : bool
        Whether to log messages to a file instead of the console.
    log_file : str
        The file path where logs should be saved if log_to_file is True.

    Returns
    -------
    logger : logging.Logger
        Configured logger instance.
    """
    if log_to_file:
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    logger = logging.getLogger(__name__)
    return logger


def filter_flows(path: str = "flows", prefixes: list = []) -> list:
    """
    Filter flow files by prefixes.

    Parameters
    ----------
    path : str
        The directory containing flow files.
    prefixes : list
        A list of prefixes to filter the flow files by. If empty, all flow files are included.

    Returns
    -------
    files : list
        A list of file paths that match the filter criteria.
    """
    files = []
    for file in os.listdir(path):
        # If no prefixes are provided, include all files.
        # Otherwise, include only files that start with any of the specified prefixes.
        if not prefixes or any(file.startswith(prefix) for prefix in prefixes):
            files.append(os.path.join(path, file))
    return files


def check_flows(
    path: str,
    exclude_domains: list,
    prefixes: list,
    logger: logging.Logger,
    verbose: bool,
) -> bool:
    """
    Process flow files and log requests to excluded domains.

    Parameters
    ----------
    path : str
        The directory containing flow files.
    exclude_domains : list
        A list of domain strings. Requests whose hosts match any of these domains are logged.
    prefixes : list
        A list of prefixes to filter flow files by.
    logger : logging.Logger
        Logger instance for logging information, warnings, and errors.
    verbose : bool
        Whether to log additional information about the request.

    Returns
    -------
    bool
        True if any unintended flow is found, False otherwise.
    """
    unintended_flow_found = False
    # Retrieve filtered flow files based on provided prefixes
    for file_path in filter_flows(path, prefixes):
        logger.info(f"Processing flow file: {file_path}")
        try:
            with open(file_path, "rb") as f:
                freader = io.FlowReader(f)
                for flow in freader.stream():
                    # Check if the request host matches any excluded domain
                    # Using substring matching here so that partial matches count.
                    if not any(
                        domain in flow.request.pretty_host for domain in exclude_domains
                    ):
                        logger.warning(f"Flag raised: {flow.request.pretty_host}")
                        unintended_flow_found = True
                        if verbose:
                            logger.warning(f"Request URL: {flow.request.url}\n")
                            logger.warning(f"Request Method: {flow.request.method}\n")
                            logger.warning(f"Request Headers: {flow.request.headers}\n")
                            logger.warning(f"Request Content: {flow.request.content}\n")
                            logger.warning(f"Response Status Code: {flow.response.status_code}\n")
                            logger.warning(f"Response Headers: {flow.response.headers}\n")
                            logger.warning(f"Response Content: {flow.response.content}\n\n")

        except FlowReadException as e:
            logger.error(f"Flow file '{file_path}' is not a valid flow file: {e}")
        except Exception as ex:
            logger.error(f"An error occurred while processing '{file_path}': {ex}")

    return unintended_flow_found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process mitmproxy flow files.")
    parser.add_argument(
        "--path", help="Path to the mitmproxy flow files", default="flows"
    )
    parser.add_argument(
        "-e",
        "--exclude_domains",
        nargs="*",
        help="List of domains to identify and log from the flows.",
        default=["www.expensify.com", "ws-mt1.pusher.com"],
    )
    parser.add_argument(
        "-p",
        "--prefixes",
        nargs="*",
        help="List of prefixes to filter the flows.",
        default=[],
    )
    parser.add_argument(
        "--log_to_file", action="store_true", help="Log to a file instead of console."
    )
    parser.add_argument(
        "--log_file", help="Log file name if logging to a file.", default="app.log"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log additional information about the request.",
        default=False,
    )
    args = parser.parse_args()
    logger = setup_logging(args.log_to_file, args.log_file)
    unintended_flow_found = check_flows(args.path, args.exclude_domains, args.prefixes, logger, args.verbose)
    sys.exit(1 if unintended_flow_found else 0)