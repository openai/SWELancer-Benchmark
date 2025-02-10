"""
Log into a pre-existing Alcatraz machine via SSH (actually it's a pseudo terminal).
"""

import base64
import os
import select
import sys
import termios
import threading
import time
import tty

import chz
import requests
from alcatraz.clusters.swarm import DEFAULT_SWARM_PROXY_SERVER_HOST

# SERVER_URL = "http://localhost:80"
SERVER_URL = "http://" + DEFAULT_SWARM_PROXY_SERVER_HOST + "/proxy"


def main(machine_info: str) -> None:
    # Create a new session
    # response = requests.post(f"{SERVER_URL}/sessions")
    response = requests.post(
        f"{SERVER_URL}/sessions",
        json={"machine_info": machine_info},
    )
    if response.status_code != 200:
        print("Failed to create session")
        return
    session_id = response.json()["session_id"]
    print(f"Session ID: {session_id}")

    # Save original terminal settings
    old_tty = termios.tcgetattr(sys.stdin)

    try:
        # Set terminal to raw mode
        tty.setraw(sys.stdin.fileno())
        stop_event = threading.Event()
        input_thread = threading.Thread(
            target=send_input, args=(session_id, stop_event, machine_info)
        )
        input_thread.daemon = True
        input_thread.start()

        while True:
            # Poll for output
            response = requests.post(
                f"{SERVER_URL}/sessions/{session_id}/read",
                json={"machine_info": machine_info},
            )
            if response.status_code != 200:
                print("Session not found")
                break
            output = base64.b64decode(response.json()["output"])
            if output:
                os.write(sys.stdout.fileno(), output)
            time.sleep(0.1)  # Adjust polling interval as needed

    except KeyboardInterrupt:
        pass
    finally:
        # Restore original terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        # Terminate the session
        requests.post(
            f"{SERVER_URL}/sessions/{session_id}/delete",
            json={"machine_info": machine_info},
        )
        stop_event.set()
        input_thread.join()
        print()
        print("Exited")


def send_input(session_id: str, stop_event: threading.Event, machine_info: str) -> None:
    try:
        while not stop_event.is_set():
            if select.select([sys.stdin], [], [], 0.1)[0]:
                data = os.read(sys.stdin.fileno(), 1024)
                if data:
                    response = requests.post(
                        f"{SERVER_URL}/sessions/{session_id}/write",
                        json={
                            "machine_info": machine_info,
                            "data": base64.b64encode(data).decode("utf-8"),
                        },
                    )
                    if response.status_code != 200:
                        print("Failed to send input")
                        print(response.text)
                        stop_event.set()  # Stop the thread
                        break
                else:
                    break
    except Exception as e:
        print(f"Input error: {e}")


if __name__ == "__main__":
    chz.entrypoint(main)
