# mypy: ignore-errors

"""
base class for all VNC-based communication to individual machines
Copypasta from nebula with async modifications
"""

import math
import time
from contextlib import AsyncExitStack, contextmanager
from io import BytesIO
from typing import Iterator

import asyncvnc  # type: ignore
from PIL import Image
from vncdotool import api


class VNCMachine:
    """Base class for all VNC-based communication with machines"""

    def __init__(
        self,
        host: str,
        vnc_port: str,
        last_position: tuple[int, int] = (300, 400),
        vnc_password: str | None = None,
    ) -> None:
        self.host = host
        self.vnc_port = vnc_port
        self.vnc_url = f"{host}::{vnc_port}"
        self._vnc_password = vnc_password
        self.mouse_last_position = last_position

    async def __aenter__(self) -> "VNCMachine":
        self.stack = await AsyncExitStack().__aenter__()
        self.client = await self.stack.enter_async_context(
            asyncvnc.connect(self.host, int(self.vnc_port), password=self._vnc_password)
        )
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        await self.stack.__aexit__(exc_type, exc_value, exc_tb)

    def __str__(self) -> str:
        return (
            f"{type(self)}: host={self.host}, vnc_port={self.vnc_port}, "
            f"mouse_last_position={self.mouse_last_position}"
        )

    def _api_connect(self) -> api.ThreadedVNCClientProxy:
        return api.connect(self.vnc_url, self._vnc_password)

    async def ping(self) -> None:
        """
        Ping the VM to ensure it's ready for subsequent computer actions.

        On Mac, this is a no-op, but generally speaking on Windows, we want to
        ensure the machine becomes ready for VNC connections as soon as possible,
        to avoid black screens when the client begins actually using it.
        """
        pass

    async def get_screenshot(self) -> bytes:
        pixels = await self.client.screenshot()
        image = Image.fromarray(pixels)
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        return image_bytes.getvalue()

    def keyboard_input(self, text: str) -> None:
        """Send keyboard input to the VM."""
        with self._api_connect() as client:
            client.factory.force_caps = True
            for char in text:
                if char == "\n":
                    client.keyPress("enter")
                elif char == "\t":
                    client.keyPress("tab")
                else:
                    client.keyPress(char)
                time.sleep(0.06)

    def multi_key_press(self, keys: list[str]) -> None:
        """Press multiple keys on the VM."""
        with self._api_connect() as client, self.hold_keys(client, keys):
            pass

    async def move_mouse(
        self,
        destination: tuple[int, int],
        keys: list[str] | None = None,
        delay: float = 0.0002,
    ) -> None:
        """Move the mouse to the specified destination."""
        # with self.hold_keys(client, keys):
        await self._move_mouse_internal(destination, delay)

    async def mouse_click(
        self,
        position: tuple[int, int],
        action: str,
        button: int = 1,
        keys: list[str] | None = None,
    ) -> None:
        """General method for mouse actions, including move, click, and drag."""
        # with self.hold_keys(client, keys):
        await self._move_mouse_internal(position)
        if action == "click":
            if button == "1":
                self.client.mouse.click()
            else:
                self.client.mouse.right_click()
        elif action == "double_click":
            self.client.mouse.click()
            time.sleep(0.05)
            self.client.mouse.click()

    def drag_mouse(
        self,
        points: list[tuple[int, int]],
        keys: list[str] | None = None,
    ) -> None:
        """
        Drag the mouse from the start position to the end position.
        """
        if not points or len(points) < 2:
            raise ValueError("At least two points are required for a multi-point drag.")

        with self._api_connect() as client, self.hold_keys(client, keys):
            # Move to the starting point without pressing down yet.
            self._move_mouse_internal(points[0], client)

            # Begin the drag operation.
            time.sleep(0.05)
            client.mouseDown(1)
            time.sleep(0.05)

            # Iterate over all points, moving through each. The last point is where we'll release the mouse button.
            for point in points[1:]:
                self._move_mouse_internal(point, client, delay=0.005)

            # End the drag operation.
            client.mouseUp(1)
            time.sleep(0.05)

    def scroll(
        self,
        position: tuple[int, int],
        scroll_x: int,
        scroll_y: int,
        keys: list[str] | None = None,
    ) -> None:
        """
        Scroll function for macOS VM.

        Args:
        - position: A tuple (x, y) indicating the mouse position before scrolling.
        - scroll_x: Horizontal scroll. Positive values scroll right, negative values scroll left.
        - scroll_y: Vertical scroll. Positive values scroll down, negative values scroll up.
        - keys: Optional list of keys to hold down during the scroll.

        Returns:
        - None
        """
        x, y = position
        keys = keys or []

        with self._api_connect() as client:
            # Move the mouse to the desired starting position before scrolling
            self._move_mouse_internal((x, y), client)
            with self.hold_keys(client, keys):
                # Handle vertical scrolling
                if scroll_y != 0:
                    self._scroll_with_delay(scroll_y, 4 if scroll_y > 0 else 5, client)

                # Handle horizontal scrolling. Shift + vertical scroll for VNC
                if scroll_x != 0:
                    with self.hold_keys(client, ["shift"]):
                        self._scroll_with_delay(scroll_x, 4 if scroll_x > 0 else 5, client)

    def _scroll_with_delay(
        self,
        scroll_amount: int,
        direction: int,
        client: api.ThreadedVNCClientProxy,
        delay: float = 0.05,
    ) -> None:
        scroll_amount = abs(int(scroll_amount / 25))
        for _ in range(scroll_amount + 2):
            client.mousePress(direction)
            time.sleep(delay)

    async def _move_mouse_internal(
        self,
        destination: tuple[int, int],
        # client: api.ThreadedVNCClientProxy,
        delay: float = 0.0002,
    ) -> None:
        """Move the mouse to the specified destination. Internal method."""
        x1, y1 = self.mouse_last_position
        x2, y2 = destination
        steps = max(int(math.hypot(x2 - x1, y2 - y1)), 1)
        for i in range(1, steps + 1):
            self.client.mouse.move(int(x1 + (x2 - x1) * i / steps), int(y1 + (y2 - y1) * i / steps))
            time.sleep(delay)
        self.mouse_last_position = destination
        time.sleep(0.05)  # Wait for the mouse to settle

    @staticmethod
    @contextmanager
    def hold_keys(
        client: api.ThreadedVNCClientProxy, keys: list[str] | None = None
    ) -> Iterator[None]:
        """
        Context manager to hold keys down during execution and release them at the end.
        This is specifically designed to work with instances of this class.
        """
        keys = keys or []
        client.factory.force_caps = True
        try:
            for key in keys:
                client.keyDown(key)
            yield
        finally:
            for key in reversed(keys):
                client.keyUp(key)
