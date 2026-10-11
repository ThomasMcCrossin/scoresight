"""overlays.uno output: sends the new values of mapped fields to a UNO control
app's API.

update_uno() is called on the GUI thread. It only queues the commands; a
background OutputWorker sends them (latest value per command wins) through one
HTTPS session with timeouts, so a slow or unreachable UNO never blocks the UI.
"""

from collections.abc import Container

import requests

from output_worker import HTTP_TIMEOUT, OutputWorker, check_http_response
from text_detection_target import TextDetectionTargetWithResult
from sc_logging import logger
from storage import subscribe_to_data, fetch_data, unsubscribe_from_data


class UNOAPI:
    def __init__(self, endpoint, field_mapping):
        self.endpoint = endpoint
        self.field_mapping = field_mapping
        self.running = False
        self.update_same = fetch_data("scoresight.json", "uno_send_same", False)
        subscribe_to_data("scoresight.json", "uno_send_same", self.set_update_same)
        self.essentials = fetch_data("scoresight.json", "uno_essentials", False)
        subscribe_to_data("scoresight.json", "uno_essentials", self.set_essentials)
        self.uno_essentials_id = fetch_data("scoresight.json", "uno_essentials_id", "")
        subscribe_to_data(
            "scoresight.json", "uno_essentials_id", self.set_uno_essentials_id
        )
        self._session = requests.Session()  # used only by the worker thread
        self._worker = OutputWorker(
            "UNO",
            self._send_payload,
            retry_on=(requests.ConnectionError, requests.Timeout),
        )

    def set_update_same(self, update_same):
        self.update_same = update_same

    def set_essentials(self, essentials):
        self.essentials = essentials

    def set_uno_essentials_id(self, uno_essentials_id):
        self.uno_essentials_id = uno_essentials_id

    def set_field_mapping(self, field_mapping):
        logger.debug(f"Setting UNO field mapping: {field_mapping}")
        self.field_mapping = field_mapping

    def set_endpoint(self, endpoint):
        """Send to another API URL from now on. The field mapping and the running
        state are kept; commands not sent yet go to the new URL."""
        if endpoint == self.endpoint:
            return
        self.endpoint = endpoint
        # the status (and the errors logged) are about the new URL
        self._worker.reset_status()

    def update_uno(
        self,
        detection: list[TextDetectionTargetWithResult],
        resend_unchanged: Container[str] = (),
    ):
        """Queue the new values of the mapped fields. Never blocks.
        The boxes named in resend_unchanged also send an unchanged value (as
        "Send Same?" does for every box), e.g. after the outputs were paused."""
        if not self.running:
            return

        if not self.field_mapping:
            logger.debug("Field mapping is not set")
            return

        for target in detection:
            send = target.result_state == (
                TextDetectionTargetWithResult.ResultState.Success
            ) or (
                target.result_state
                == TextDetectionTargetWithResult.ResultState.SameNoChange
                and (self.update_same or target.name in resend_unchanged)
            )
            if send and target.name in self.field_mapping:
                uno_command = self.field_mapping[target.name]
                if uno_command:
                    self.send_uno_command(uno_command, target.result)

    def payload_for(self, command, value) -> dict:
        if not self.essentials:
            return {"command": command, "value": value}
        return {
            "command": "SetOverlayContentField",
            "value": value,
            "fieldId": command,
            "id": self.uno_essentials_id,
        }

    def send_uno_command(self, command, value):
        """Queue command with value for sending in the background."""
        self._worker.submit(command, self.payload_for(command, value))

    def _send_payload(self, command, payload) -> None:
        # runs on the worker thread
        response = self._session.put(self.endpoint, json=payload, timeout=HTTP_TIMEOUT)
        # Check rate limit headers
        self.check_rate_limits(response.headers)
        check_http_response(response, f"UNO {command}")
        logger.debug(f"Successfully sent {command}: {payload['value']} to UNO API")

    def check_rate_limits(self, headers):
        rate_limit_headers = [
            "X-Singular-Ratelimit-Burst-Calls",
            "X-Singular-Ratelimit-Daily-Calls",
            "X-Singular-Ratelimit-Burst-Data",
            "X-Singular-Ratelimit-Daily-Data",
        ]

        for header in rate_limit_headers:
            if header in headers:
                limit_info = headers[header]
                logger.debug(f"Rate limit info for {header}: {limit_info}")

                # You can add more sophisticated rate limit handling here if needed
                # For example, pause requests if limits are close to being reached

    def start(self):
        self.running = True

    def stop(self):
        self.running = False
        self._worker.clear()
        self._worker.reset_status()

    def status(self):
        """The sending's WorkerStatus (see output_worker)."""
        return self._worker.status()

    def close(self):
        """Stop sending and unsubscribe from settings changes."""
        self.stop()
        unsubscribe_from_data("scoresight.json", "uno_send_same", self.set_update_same)
        unsubscribe_from_data("scoresight.json", "uno_essentials", self.set_essentials)
        unsubscribe_from_data(
            "scoresight.json", "uno_essentials_id", self.set_uno_essentials_id
        )
        self._worker.stop()
