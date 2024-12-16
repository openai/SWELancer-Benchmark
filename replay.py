import os
import base64
import calendar
import gzip
import json
import logging
import re
import threading
import time
import itertools
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from io import BytesIO

import pusher
from mitmproxy import http, io
from mitmproxy.exceptions import FlowReadException
from nacl.exceptions import CryptoError
from nacl.secret import SecretBox
from requests_toolbelt.multipart import decoder
from bs4 import BeautifulSoup

# Important! Set the flow file name here
ISSUE_ID = os.environ.get("ISSUE_ID")
FLOW_FILE_PATH = f"/app/tests/issues/{ISSUE_ID}/flow.mitm"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
for handler in logger.handlers:
    handler.setFormatter(logging.Formatter("%(filename)s:%(lineno)s - %(message)s"))

# Constants
API_PREFIXES = ["/api/{0}", "/api?command={0}"]
API_FORMAT_LAMBDA = lambda x: [prefix.format(x) for prefix in API_PREFIXES]
API_FORMAT_BYTES_LAMBDA = lambda x: [prefix.format(x).encode() for prefix in API_PREFIXES]
REQUESTS_TO_MATCH = ["/api", "/chat-attachments/", "/receipts/"]

EXPENSIFY_HOSTS = ["www.expensify.com"]
WEBSOCKET_HOSTS = ["ws-mt1.pusher.com"]

UNNECESSARY_PATHS = list(
    itertools.chain.from_iterable(
        [API_FORMAT_BYTES_LAMBDA(x) for x in ["Log", "Ping", "LogOut"]]
    )
)
DUPLICATE_HANDLE_PATHS = list(
    itertools.chain.from_iterable(
        [API_FORMAT_BYTES_LAMBDA(x) for x in ["OpenReport", "GetPolicy"]]
    )
)
PUSHER_AUTHENTICATION_PATHS = list(
    itertools.chain.from_iterable(
        [API_FORMAT_BYTES_LAMBDA(x) for x in ["AuthenticatePusher"]]
    )
)
SKIPPABLE_PATHS = list(
    itertools.chain.from_iterable(
        [
            API_FORMAT_LAMBDA(x)
            for x in [
                "ReadNewestAction",
                "AuthenticatePusher",
                "GetMissingOnyxMessages",
                "OpenReport",
            ]
        ]
    )
)

DUPLICATE_HANDLE_KEYS = ["reportID", "policyID"]
CHAT_ATTACHMENTS_PATHS = [b"/chat-attachments/", b"/receipts/"]

DATES_REGEX = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}"
DATES_REGEX_NO_MILLIS = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
AUTH_REGEX = r'"auth": ".+"'
GARBAGE_IDS = [None, "", "null", "0", "-1"]

# Dynamic Content Constants
DYNAMIC_CONTENT_KEYS = ["reportComment", "glCode"]
DYNAMIC_CONTENT_REPLACEMENTS = {}

# Context
REPLACEMENT_VARS = {}
REPLACEMENT_DATES = {}
REPLACEMENT_TIMESTAMPS = {}

# Websockets
WS_TASKS = set()

# Pusher Tokens
PUSHER_APP_KEY = os.environ.get("PUSHER_APP_KEY")
PUSHER_APP_SECRET = os.environ.get("PUSHER_APP_SECRET")
PUSHER_APP_ID = os.environ.get("PUSHER_APP_ID")
PUSHER_CLUSTER = "mt1"
PUSHER_ENCRYPTION_MASTER_KEY = "M1FtOU1Wd3kycjV3dWdoS05zQkh0MVJKcTJiVFFIQXQ="


class PusherDecryptionUtils:
    @staticmethod
    def decrypt_pusher_notification(shared_key: str, notification: str) -> str:
        """
        Decrypts a Pusher notification using NaCl SecretBox.

        :param shared_key: The shared encryption key (Base64-encoded).
        :param notification: The raw Pusher notification (JSON string).
        :return: The decrypted plaintext message as a string.
        """
        # Parse the JSON notification
        try:
            notification_data = json.loads(notification)
            encrypted_data = json.loads(notification_data["data"])
            nonce = encrypted_data["nonce"]
            ciphertext = encrypted_data["ciphertext"]
        except (KeyError, ValueError) as e:
            raise Exception(f"Failed to parse notification: {e}")

        # Decode the shared key, nonce, and ciphertext from Base64
        key = base64.b64decode(shared_key)
        nonce = base64.b64decode(nonce)
        encrypted_message = base64.b64decode(ciphertext)

        # Create a SecretBox object with the shared key
        box = SecretBox(key)

        # Decrypt the message
        try:
            plaintext = box.decrypt(encrypted_message, nonce)
            return plaintext.decode("utf-8")
        except CryptoError as e:
            raise Exception(f"Decryption failed: {e}")


class ExpensifyReplay:
    def __init__(self, flow_file_path):
        """
        Initialize the ExpensifyReplay addon.

        Args:
            flow_file_path (str): Path to the mitmproxy flow dump file.
        """
        self.flow_file_path = flow_file_path
        self.recorded_flows = []
        self.filtered_flows = []
        self.attachment_flows = []
        self.duplicate_handle_flows = []
        self.other_flows = []
        self.ws_flows = []
        self.pusher_auth_flows = []
        self.smallest_date = None
        self.load_recorded_flows()
        self.current_date = None
        try:
            self.pusher_client = pusher.Pusher(
                app_id=PUSHER_APP_ID,
                key=PUSHER_APP_KEY,
                secret=PUSHER_APP_SECRET,
                cluster=PUSHER_CLUSTER,
                ssl=True,
                encryption_master_key_base64=PUSHER_ENCRYPTION_MASTER_KEY,
            )
        except:
            self.pusher_client = None
            logger.warning(
                "Failed to initialize Pusher client, WS messages will not be injected."
            )
        logger.info(f"Loaded {len(self.recorded_flows)} recorded flows")
        logger.info(f"Unique email addresses: {list(self.email_based_flows.keys())}")
        logger.info(f"Flow recorded on: {self.smallest_date}")
        logger.info(
            f"Loaded decryption keys for {len(self.pusher_decryption_keys)} Pusher channels"
        )

    def load_recorded_flows(self):
        """
        Load recorded flows from the mitmproxy dump file.
        """
        try:
            with open(self.flow_file_path, "rb") as f:
                flow_reader = io.FlowReader(f)
                for flow in flow_reader.stream():
                    self.recorded_flows.append(flow.get_state())
            self.process_flows()
        except FlowReadException as e:
            logger.error(f"Error reading mitm file: {e}")

    def get_date_from_recorded_flow(self, flow):
        """
        Get the date from the recorded flow.

        Args:
            flow (dict): The recorded flow.

        Returns:
            datetime: The date extracted from the headers.
        """
        timestamp_created = flow["timestamp_created"]
        # Convert to datetime
        return datetime.utcfromtimestamp(timestamp_created)

    def process_flows(self):
        """
        Process the recorded flows, separating them into filtered and other flows.
        """
        # First, decompress the content of the flows
        for flow in self.recorded_flows:
            if not flow["response"]:
                continue
            flow["response"]["content"] = self.decompress_gzip(
                flow["response"]["content"], flow["response"]["headers"]
            )
            if isinstance(flow["response"]["content"], str):
                flow["response"]["content"] = (
                    flow["response"]["content"]
                    .encode("utf-16", "surrogatepass")
                    .decode("utf-16")
                )
                flow["response"]["content"] = flow["response"]["content"].replace(
                    r"\/", "/"
                )

        for flow in self.recorded_flows:
            if "method" not in flow["request"]:
                continue
            elif flow["websocket"] and any(
                host in flow["server_conn"]["sni"] for host in WEBSOCKET_HOSTS
            ):
                self.ws_flows.append(flow)
            elif flow["server_conn"]["sni"] not in EXPENSIFY_HOSTS:
                self.other_flows.append(flow)
            elif any(
                flow["request"]["path"].startswith(path) for path in UNNECESSARY_PATHS
            ):
                self.other_flows.append(flow)
            elif any(
                flow["request"]["path"].startswith(path)
                for path in CHAT_ATTACHMENTS_PATHS
            ):
                self.attachment_flows.append(flow)
            else:
                self.filtered_flows.append({"flow": flow, "marked": False})
                if any(
                    flow["request"]["path"].startswith(path)
                    for path in PUSHER_AUTHENTICATION_PATHS
                ):
                    self.pusher_auth_flows.append(flow)

        # Extract date from headers from both flows
        dates = []

        for flow in self.filtered_flows:
            date = self.get_date_from_recorded_flow(flow["flow"])
            if date:
                dates.append(date)

        for flow in self.other_flows:
            date = self.get_date_from_recorded_flow(flow)
            if date:
                dates.append(date)

        if dates:
            self.smallest_date = min(dates)
            self.smallest_date_ts = calendar.timegm(self.smallest_date.timetuple())

        # For attachment flows remove everything after ? in the path
        # That is the authenticaion token and we don't need to store that
        for flow in self.attachment_flows:
            path = flow["request"]["path"].decode().split("?")[0]
            flow["request"]["path"] = path.encode()

        # For WS flows, keep only server-initiated messages
        for flow in self.ws_flows:
            messages = flow["websocket"]["messages"]
            flow["websocket"]["messages"] = [
                list(msg) for msg in messages if msg[1] is False
            ]
            flow["websocket"]["reserved"] = False

        # Sort the flows by timestamp
        self.filtered_flows.sort(key=lambda x: x["flow"]["request"]["timestamp_start"])
        self.other_flows.sort(key=lambda x: x["request"]["timestamp_start"])

        # Further bucket into email-based flows
        self.email_based_flows = defaultdict(list)
        for flow_entry in self.filtered_flows:
            flow = flow_entry["flow"]
            headers = self.convert_headers_to_dict(flow["request"]["headers"])
            if self.is_multipart_form_data(headers) or self.is_x_www_form_urlencoded(
                headers
            ):
                email = self.get_email_from_request(
                    flow["request"]["content"],
                    headers.get(b"content-type", b"").decode("utf-8"),
                )
                if email:
                    self.email_based_flows[email].append(flow_entry)

        # Further bucket to handle duplicate calls
        self.duplicate_handle_flows = defaultdict(dict)
        for flow_entry in self.filtered_flows:
            flow = flow_entry["flow"]
            headers = self.convert_headers_to_dict(flow["request"]["headers"])
            if any(path in flow["request"]["path"] for path in DUPLICATE_HANDLE_PATHS):
                for key in DUPLICATE_HANDLE_KEYS:
                    unique_ids = self.extract_unique_ids(
                        flow["request"]["content"],
                        headers.get(b"content-type", b"").decode("utf-8"),
                    )
                    value = unique_ids.get(key)
                    update_id = unique_ids.get("clientUpdateID")
                    if value:
                        # The goal is to cache the last flow for each key
                        self.duplicate_handle_flows[(value, update_id)] = flow_entry

        # Create a map of channel to key for Pusher flows
        self.create_channel_key_map()

        # Decrypt Pusher messages
        self.decrypt_websocket_messages()

    def create_channel_key_map(self):
        """
        Read Pusher Authentication flows and create a map of channel to key.
        Store the map to each websocket flow for decryption.
        """
        self.pusher_decryption_keys = {}
        for flow in self.pusher_auth_flows:
            # Read the flow request content
            content = flow["request"]["content"]
            headers = self.convert_headers_to_dict(flow["request"]["headers"])
            # Extract channel and key
            ids = self.extract_unique_ids(
                content,
                headers.get(b"content-type", b"").decode("utf-8"),
                get_pusher_ids=True,
            )
            channel = ids.get("channel_name")
            # Channel must contain -encrypted- to be encrypted
            if "-encrypted-" not in channel:
                continue
            # Load the response as JSON
            try:
                response = json.loads(flow["response"]["content"])
                key = response.get("shared_secret")
                if not key:
                    continue
                self.pusher_decryption_keys[channel] = key
            except Exception as e:
                logger.warning(f"Failed to load Pusher response: {e}")

    def decrypt_websocket_messages(self):
        """
        Decrypt all websocket messages which have channel name containing -encrypted-.
        """
        decryption_count = 0
        for flow in self.ws_flows:
            messages = flow["websocket"]["messages"]
            for msg in messages:
                msg_json = json.loads(msg[2])
                channel = msg_json.get("channel")
                if channel in self.pusher_decryption_keys:
                    key = self.pusher_decryption_keys[channel]
                    try:
                        decrypted = PusherDecryptionUtils.decrypt_pusher_notification(
                            key, msg[2]
                        )
                        msg_json["data"] = json.loads(decrypted)
                        decryption_count += 1
                    except Exception as e:
                        pass
                msg[2] = msg_json
        logger.info(f"Decrypted {decryption_count} Pusher messages")

    def decompress_gzip(self, compressed_content, headers=None):
        """
        Decompress Gzip-encoded content.

        Args:
            compressed_content (bytes): Gzip compressed data.
            headers: HTTP headers.

        Returns:
            bytes: Decompressed data.
        """
        if headers:
            headers = self.convert_headers_to_dict(headers)
            content_encoding = headers.get(b"content-encoding", b"").decode("utf-8")
            if "gzip" not in content_encoding:
                return compressed_content

        # Content can be previously decompressed too. Return if it's not gzip
        if isinstance(compressed_content, str):
            return compressed_content

        try:
            with gzip.GzipFile(fileobj=BytesIO(compressed_content)) as f:
                return f.read().decode("utf-8")
        except Exception:
            try:
                # Possible compressed bytes data:
                with gzip.GzipFile(fileobj=BytesIO(compressed_content)) as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to decompress content: {e}")

        # Return as it is if decompression fails
        return compressed_content

    def inject_ws(self, flow: http.HTTPFlow, ws_flow):
        """
        Inject a WebSocket message.

        Args:
            flow (http.HTTPFlow): The HTTP flow.
            ws_flow (dict): The WebSocket flow.
        """
        if not self.pusher_client:
            logger.warning("Pusher client not initialized, cannot inject WS messages.")
            return

        ws_messages = ws_flow["websocket"]["messages"]
        current_date = calendar.timegm(datetime.utcnow().timetuple())
        # Update timestamps for the WS messages
        smallest_ts = min(msg[3] for msg in ws_messages) - 1
        for msg in ws_messages:
            msg[3] = current_date + (msg[3] - smallest_ts)
        while True:
            _now = datetime.utcnow()
            _ts = calendar.timegm(_now.timetuple())
            if not ws_messages:
                logger.info(f"Finished injecting WS messages to {ws_flow['id']}")
                break
            if ws_messages[0][3] <= _ts:
                # Get JSON message
                msg = ws_messages.pop(0)
                msg_json = msg[2]
                channel_name = msg_json.get("channel", "")
                event = msg_json.get("event", "")
                if not channel_name or event.startswith("pusher"):
                    continue
                # Perform ID replacement
                for key, value in REPLACEMENT_VARS.items():
                    channel_name = channel_name.replace(key, value)
                # Perform data replacement on the data
                data = msg_json.get("data")
                if not data:
                    continue
                data = self.replace_dates(json.dumps(data))
                for key, value in REPLACEMENT_VARS.items():
                    data = data.replace(key, value)
                self.pusher_client.trigger(channel_name, event, json.loads(data))
                logger.info(f"Injected WS message to {channel_name}")
            time.sleep(0.5)

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Handle incoming HTTP requests.

        Args:
            flow (http.HTTPFlow): The HTTP flow.
        """
        # First check if incoming request is for WS
        ws_match = any(host in flow.request.url for host in WEBSOCKET_HOSTS)
        if ws_match:
            logger.info(f"Intercepted WS request to {flow.request.url}")
            for ws_flow in self.ws_flows:
                if ws_flow["websocket"]["reserved"]:
                    continue
                if ws_flow["server_conn"]["address"] == flow.server_conn.address:
                    ws_flow["websocket"]["reserved"] = True
                    t = threading.Thread(target=self.inject_ws, args=(flow, ws_flow))
                    t.start()
                    WS_TASKS.add(t)
                    logger.info(f"Reserved WS flow: {ws_flow['id']}")
                    return

        host_matched = any(host in flow.request.pretty_host for host in EXPENSIFY_HOSTS)
        if (
            host_matched
            and any(path in flow.request.path for path in REQUESTS_TO_MATCH)
            and flow.request.method != "OPTIONS"
        ):
            logger.info(f"Intercepted request to {flow.request.url}")
            if self.current_date is None:
                self.current_date = datetime.utcnow()
            recorded_response = self.find_matching_response(flow)
            try:
                content = recorded_response["response"]["content"]
            except Exception:
                content = json.dumps({})
            try:
                response_code = recorded_response["response"]["status_code"]
            except Exception:
                response_code = 200
            try:
                headers = recorded_response["response"]["headers"]
            except Exception:
                headers = {}
            flow.response = http.Response.make(response_code, content, dict(headers))

    def find_matching_response(self, request_flow: http.HTTPFlow):
        """
        Find a matching response from the recorded flows for the given request.

        Args:
            request_flow (http.HTTPFlow): The incoming HTTP request flow.

        Returns:
            dict: The matching recorded flow, or None if not found.
        """
        request_method = request_flow.request.method.encode("utf-8")
        request_url = request_flow.request.url

        # First, check in other_flows
        for flow in self.other_flows:
            recorded_method = flow["request"]["method"]
            recorded_url = self.construct_url(flow)
            if recorded_method == request_method and recorded_url == request_url:
                return flow

        # Now check in attachment_flows
        for flow in self.attachment_flows:
            recorded_method = flow["request"]["method"]
            recorded_url = self.construct_url(flow)
            # Strip request URL to match
            request_url_match = request_url.split("?")[0]
            # In recorded URL perform ID replacement
            for key, value in REPLACEMENT_VARS.items():
                recorded_url = recorded_url.replace(key, value)
            if recorded_method == request_method and recorded_url == request_url_match:
                return flow

        # Then, check in filtered_flows
        request_content = request_flow.request.content
        content_type = request_flow.request.headers.get("Content-Type", "")
        flow_entry = self.find_matching_flow(
            request_method, request_url, request_content, content_type
        )
        if flow_entry is None:
            return None

        matching_flow = flow_entry["flow"]

        if not matching_flow["response"]:
            return matching_flow

        matching_flow_headers = self.convert_headers_to_dict(
            matching_flow["request"]["headers"]
        )
        if self.is_multipart_form_data(
            matching_flow_headers
        ) or self.is_x_www_form_urlencoded(matching_flow_headers):
            # We do not want to tamper original matching flow, thus create a copy
            matching_flow = deepcopy(matching_flow)
            self.replace_unique_ids(request_flow, matching_flow)

        # If content is ignored, undo
        if matching_flow["response"]["content"] == "IGNORED":
            flow_entry["marked"] = False
            matching_flow["response"]["content"] = json.dumps({})

        return matching_flow

    def find_matching_flow(
        self, request_method, request_url, request_content, content_type
    ):
        """
        Find a matching flow in the filtered_flows.
        Args:
            request_method (bytes): The request method.
            request_url (str): The request URL.
            request_content (bytes): The request content.
            content_type (str): The content type header value.
        Returns:
            dict: The matching flow, or None.
        """
        # Choose which email flows to use
        email = self.get_email_from_request(request_content, content_type)
        if email and email in self.email_based_flows:
            flows = self.email_based_flows[email]
        else:
            flows = self.filtered_flows

        for flow_entry in flows:
            flow = flow_entry["flow"]
            recorded_method = flow["request"]["method"]
            recorded_url = self.construct_url(flow)
            matched = recorded_method == request_method and recorded_url == request_url
            matched_skip = any(path in recorded_url for path in SKIPPABLE_PATHS)
            if flow_entry["marked"]:
                continue
            elif matched:
                flow_entry["marked"] = True
                return flow_entry
            elif matched_skip:
                continue  # Match later
            else:
                break

        # If we are here then no match was found, but sometimes duplicated calls can be expected,
        # especially for endpoints such as OpenReport. Specifically handle those endpoints.
        if any(path.decode() in request_url for path in DUPLICATE_HANDLE_PATHS):
            unique_ids = self.extract_unique_ids(request_content, content_type)
            # The unique_ids are replaced IDs, so fetch the original ones
            for k, v in unique_ids.items():
                # Get v's old value from Replacement Vars
                for _k, _v in REPLACEMENT_VARS.items():
                    if _v == v:
                        unique_ids[k] = _k
            for key in DUPLICATE_HANDLE_KEYS:
                value = unique_ids.get(key)
                update_id = unique_ids.get("clientUpdateID")
                matching_flow = self.duplicate_handle_flows.get((value, update_id))
                if matching_flow:
                    # Remove the flow from the cache
                    return matching_flow

        if any(path in request_url for path in SKIPPABLE_PATHS):
            return None

        # Last resort, if we are here, it means that the FE is either making a call that was not recorded
        # or that the order of calls is different. In such cases, we can return the first unmarked flow
        # Ideally, this should not happen and the test must be recorded again with a slow_mo parameter
        # set to ensure that the order of calls is maintained
        to_mark = []
        marked_flow = None
        # Iterate over non-marked flows, find the matching one,
        # and set all upto that as marked
        for flow_entry in flows:
            flow = flow_entry["flow"]
            recorded_method = flow["request"]["method"]
            recorded_url = self.construct_url(flow)
            matched = recorded_method == request_method and recorded_url == request_url
            if flow_entry["marked"]:
                continue
            else:
                if matched:
                    flow_entry["marked"] = True
                    marked_flow = flow_entry
                    break
                else:
                    to_mark.append(flow_entry)

        if marked_flow:
            for flow_entry in to_mark:
                flow_entry["marked"] = True

        return marked_flow

    def construct_url(self, flow):
        """
        Construct the full URL from the flow data.

        Args:
            flow (dict): The flow data.

        Returns:
            str: The full URL.
        """
        host = EXPENSIFY_HOSTS[0].encode("utf-8")
        return (
            flow["request"]["scheme"] + b"://" + host + flow["request"]["path"]
        ).decode("utf-8")

    def convert_headers_to_dict(self, headers: any) -> dict:
        """
        Convert headers to a dictionary.

        Args:
            headers (any): Headers to convert.

        Returns:
            dict: Dictionary of headers.
        """
        if isinstance(headers, dict):
            return headers
        return {k: v for k, v in headers}

    def is_multipart_form_data(self, headers):
        """
        Check if the content type is multipart/form-data.

        Args:
            headers (dict): HTTP headers.

        Returns:
            bool: True if content type is multipart/form-data, False otherwise.
        """
        content_type = headers.get(b"content-type", b"").decode("utf-8")
        return "multipart/form-data" in content_type

    def is_x_www_form_urlencoded(self, headers):
        """
        Check if the content type is application/x-www-form-urlencoded.

        Args:
            headers (dict): HTTP headers.

        Returns:
            bool: True if content type is application/x-www-form-urlencoded, False otherwise.
        """
        content_type = headers.get(b"content-type", b"").decode("utf-8")
        return "application/x-www-form-urlencoded" in content_type

    def replace_unique_ids(self, request_flow, recorded_flow):
        """
        Replace unique IDs in the response content based on the request content.

        Args:
            request_flow (http.HTTPFlow): The incoming request flow.
            recorded_flow (dict): The recorded flow to modify.
        """
        # Extract IDs from recorded request
        recorded_headers = self.convert_headers_to_dict(
            recorded_flow["request"]["headers"]
        )
        recorded_content = recorded_flow["request"]["content"]
        recorded_content_type = recorded_headers.get(b"content-type", b"").decode(
            "utf-8"
        )
        recorded_ids = self.extract_unique_ids(recorded_content, recorded_content_type)

        # Extract IDs from incoming request
        request_content = request_flow.request.content
        request_headers = request_flow.request.headers
        request_content_type = request_headers.get("Content-Type", "")
        request_ids = self.extract_unique_ids(request_content, request_content_type)

        if recorded_flow["response"] is None:
            flow_url = request_flow.request.url
            logger.warning(f"Missing response for flow recorded on: {flow_url}")
            return

        response_content = recorded_flow["response"]["content"]

        if type(response_content) != str:
            return

        # Replace IDs in response content
        current_repl_vars = set(REPLACEMENT_VARS.values())
        for name, value in recorded_ids.items():
            request_value = request_ids.get(name)
            if request_value:
                if request_value not in current_repl_vars:
                    # Store the replaced value for future reference
                    REPLACEMENT_VARS[value] = request_value

        # Force replacement of some keys
        # In certain scenarios, the app is requesting the BE for updates and these requests do not have any unique IDs
        # Thus, we need to force replacement so that the policy and report IDs match properly
        for key, value in REPLACEMENT_VARS.items():
            response_content = response_content.replace(key, value)

        # I hate ReadNewestAction endpoint, it messes EVERYTHING up.
        # In the upcoming request, get the ReportID and ensure we have a replacement for it
        # If we don't return empty
        if "ReadNewestAction?" in request_flow.request.path:
            # If nothing replaced, return
            report_id = request_ids.get("reportID")
            if report_id not in response_content:
                recorded_flow["response"]["content"] = "IGNORED"
                return

        # Replace dates in the response content
        response_content = self.replace_dates(response_content)

        # Special case to handle Pusher flows
        if (
            "AuthenticatePusher" in request_flow.request.path
            and self.pusher_client is not None
        ):
            response_content = self.handle_pusher_flows(request_flow, response_content)

        # Replace dynamic content
        response_content = self.replace_dynamic_content(
            request_content,
            request_content_type,
            recorded_content,
            recorded_content_type,
            response_content,
        )

        # Update the response content
        recorded_flow["response"]["content"] = response_content

    def handle_pusher_flows(self, request_flow, response_content):
        # From request flow get pusher IDs
        request_content = request_flow.request.content
        request_headers = request_flow.request.headers
        request_content_type = request_headers.get("Content-Type", "")
        request_ids = self.extract_unique_ids(
            request_content, request_content_type, get_pusher_ids=True
        )

        socket_id = request_ids.get("socket_id")
        channel = request_ids.get("channel_name")

        # Generate auth for the subscription key
        auth = self.pusher_client.authenticate(channel=channel, socket_id=socket_id)

        # Update the recorded flow with the auth
        response_content = json.loads(response_content)
        response_content.update(auth)
        if "shared_secret" in response_content and not isinstance(
            response_content["shared_secret"], str
        ):
            response_content["shared_secret"] = response_content[
                "shared_secret"
            ].decode("utf-8")

        return json.dumps(response_content)

    def replace_dates(self, content):
        """
        Replace dates in the content.

        Args:
            content (str): The content to modify.

        Returns:
            str: The modified content.
        """
        # Run regex on the content to find dates
        matches = re.findall(DATES_REGEX, content)
        matches_2 = re.findall(DATES_REGEX_NO_MILLIS, content)

        if not matches and not matches_2:
            return content

        def convert_timestamp_to_string(timestamp):
            timestamp = str(timestamp)[:14]
            if timestamp.endswith(".0"):
                timestamp = timestamp[:-2]
            else:
                timestamp = timestamp.replace(".", "")
            return timestamp

        def perform_dates_replacement(matches, format, content):
            smallest_date = self.smallest_date
            matches = list(set(matches))

            for match in matches:
                match_date = datetime.strptime(match, format)
                match_timestamp = (
                    calendar.timegm(match_date.timetuple())
                    + match_date.microsecond / 1_000_000
                )
                match_timestamp = convert_timestamp_to_string(match_timestamp)

                # Check if the date is already cached
                if match in REPLACEMENT_DATES:
                    new_date = REPLACEMENT_DATES[match]
                    new_timestamp = REPLACEMENT_TIMESTAMPS[match_timestamp]
                else:
                    # Calculate the difference and the new date
                    diff = match_date - smallest_date
                    if diff < timedelta(0):
                        continue
                    new_date = (self.current_date + diff).strftime(format)[: len(match)]
                    new_timestamp_value = (
                        calendar.timegm((self.current_date + diff).timetuple())
                        + (self.current_date + diff).microsecond / 1_000_000
                    )
                    new_timestamp = convert_timestamp_to_string(new_timestamp_value)

                    # Cache the replacements
                    REPLACEMENT_DATES[match] = new_date
                    REPLACEMENT_TIMESTAMPS[
                        convert_timestamp_to_string(match_timestamp)
                    ] = new_timestamp

                # Replace in the content
                content = content.replace(match, new_date)
                content = content.replace(match_timestamp, new_timestamp)

            return content

        content = perform_dates_replacement(matches, "%Y-%m-%d %H:%M:%S.%f", content)
        content = perform_dates_replacement(matches_2, "%Y-%m-%d %H:%M:%S", content)

        return content

    def convert_data_to_dict(self, content, content_type):
        """
        Convert data to a dictionary.

        Args:
            content (bytes): The data to convert.
            content_type (str): The content type header value.

        Returns:
            dict: The converted data.
        """
        data = {}
        try:
            if content_type.startswith("application/json"):
                data = json.loads(content)
            elif content_type.startswith("multipart/form-data"):
                decoded_content = decoder.MultipartDecoder(
                    content=content, content_type=content_type
                )
                name_pattern = re.compile(r'name="(.+?)"')
                for part in decoded_content.parts:
                    try:
                        text = part.text
                    except UnicodeDecodeError:
                        # Attachment data is binary, and we don't need to process it
                        continue
                    headers = part.headers.get(b"Content-Disposition", b"").decode()
                    match = name_pattern.search(headers)
                    if not match:
                        continue
                    name = match.group(1)
                    data[name] = text
            elif content_type.startswith("application/x-www-form-urlencoded"):
                content_str = content.decode("utf-8")
                for pair in content_str.split("&"):
                    name, value = pair.split("=")
                    if not name:
                        continue
                    data[name] = value
        except Exception as e:
            logger.warning(f"Failed to convert data: {e}")
        return data

    def extract_unique_ids(self, content, content_type, get_pusher_ids=False):
        """
        Extract unique IDs from multipart/form-data or x-www-form-urlencoded content.

        Args:
            content (bytes): The content to parse.
            content_type (str): The content type header value.
            get_pusher_ids (bool): Whether to extract Pusher IDs.

        Returns:
            dict: A dictionary of unique IDs and their values.
        """
        unique_ids = {}
        data = self.convert_data_to_dict(content, content_type)

        # Extract IDs from the data
        for key, value in data.items():
            if not key or value in GARBAGE_IDS:
                continue
            if "ID" in key:
                unique_ids[key] = value
            if get_pusher_ids:
                if "channel" in key:
                    unique_ids[key] = value
                if "socket_id" in key:
                    unique_ids[key] = value

        return unique_ids

    def replace_dynamic_content(
        self,
        request_data,
        request_data_type,
        response_data,
        response_data_type,
        response_content,
    ):
        # Get the dynamic content from the request
        request = self.convert_data_to_dict(request_data, request_data_type)
        response = self.convert_data_to_dict(response_data, response_data_type)

        for key in DYNAMIC_CONTENT_KEYS:
            request_value = request.get(key)
            if not request_value:
                continue
            response_value = response.get(key)
            DYNAMIC_CONTENT_REPLACEMENTS[response_value] = request_value

            # Sometimes the content might have HTML tags, strip them and store
            mod_request_value = BeautifulSoup(request_value, "lxml").text
            if not mod_request_value:
                continue
            mod_response_value = BeautifulSoup(response_value, "lxml").text
            DYNAMIC_CONTENT_REPLACEMENTS[mod_response_value] = mod_request_value

        # Replace the dynamic content in the response
        for key, value in DYNAMIC_CONTENT_REPLACEMENTS.items():
            response_content = response_content.replace(key, value)

        return response_content

    def get_email_from_request(self, request_content, content_type):
        """
        Extract email address from the request content.

        Args:
            request_content (bytes): The request content.
            content_type (str): The content type header value.

        Returns:
            str: The email address.
        """
        email = None
        try:
            if content_type.startswith("multipart/form-data"):
                decoded_content = decoder.MultipartDecoder(
                    content=request_content, content_type=content_type
                )
                for part in decoded_content.parts:
                    headers = part.headers.get(b"Content-Disposition", b"").decode()
                    if "email" in headers:
                        email = part.text
            elif content_type.startswith("application/x-www-form-urlencoded"):
                content_str = request_content.decode("utf-8")
                for pair in content_str.split("&"):
                    name, value = pair.split("=")
                    if "email" in name:
                        email = value
        except Exception as e:
            logger.warning(f"Failed to extract email: {e}")
        return email


# Add the addon to mitmproxy
addons = [ExpensifyReplay(FLOW_FILE_PATH)]
