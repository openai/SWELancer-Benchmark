#!/bin/bash

set -e
if [ "$EVAL_VARIANT" = "swe_manager" ]; then
    echo "EVAL_VARIANT is set to swe_manager. Skipping setup steps."
else
    # Start Xvfb for a virtual display
    echo "Starting Xvfb on display :99..."
    Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
    export DISPLAY=:99
    sleep 2

    # Start a lightweight window manager
    echo "Starting Fluxbox window manager..."
    fluxbox > /dev/null 2>&1 &
    sleep 2

    # Start x11vnc to expose the Xvfb display
    echo "Starting x11vnc server..."
    x11vnc -display :99 -forever -rfbport 5900 -noxdamage > /dev/null 2>&1 &
    sleep 2

    # Start NoVNC to allow browser access
    echo "Starting NoVNC..."
    websockify --web=/usr/share/novnc/ 5901 localhost:5900 > /dev/null 2>&1 &
    sleep 2

    # Create aliases 
    echo "alias user-tool='ansible-playbook -i \"localhost,\" --connection=local /app/tests/run_user_tool.yml'" >> ~/.bashrc

    # Run ansible playbooks to setup expensify and mitmproxy
    ansible-playbook -i "localhost," --connection=local /app/tests/setup_expensify.yml
    ansible-playbook -i "localhost," --connection=local /app/tests/setup_mitmproxy.yml

    # Set an environment variable to indicate that the setup is done
    echo "done" > /setup_done.txt
fi

# Start bash
tail -f /dev/null
