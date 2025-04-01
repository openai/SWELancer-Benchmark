#!/bin/bash

set -e
if [ "$EVAL_VARIANT" = "swe_manager" ]; then
    echo "EVAL_VARIANT is set to swe_manager. Skipping setup steps."
else
    # Start Xvfb for a virtual display
    echo "Starting Xvfb on display :99..."
    Xvfb :99 -screen 0 2560x1600x24 > /dev/null 2>&1 &
    export DISPLAY=:99
    sleep 2

    # Start bspwm window manager
    echo "Starting bspwm window manager..."
    bspwm > /dev/null 2>&1 &
    sleep 2

    # Start x11vnc to expose the Xvfb display
    echo "Starting x11vnc server..."
    x11vnc -display :99 -forever -rfbport 5900 -noxdamage > /dev/null 2>&1 &
    sleep 2

    # Start NoVNC to allow browser access
    echo "Starting NoVNC..."
    websockify --web=/usr/share/novnc/ 5901 localhost:5900 > /dev/null 2>&1 &
    sleep 2

    # Modify host file to point to ws-mt1.pusher.com
    echo "127.0.0.1 ws-mt1.pusher.com" >> /etc/hosts

    # Start Pusher-Fake in the background
    echo "Starting Pusher-Fake service..."
    cd /app/ # Do not set this to where the EXP repo is cloned, as it causes gem conflicts
    pusher-fake --id $PUSHER_APP_ID --key $PUSHER_APP_KEY --secret $PUSHER_APP_SECRET \
        --web-host 0.0.0.0 --web-port 57004 \
        --socket-host 0.0.0.0 --socket-port 57003 --verbose > /dev/null 2>&1 &

    # Start NGINX
    nginx -g "daemon off;" > /dev/null 2>&1 &
    sleep 2

    # Create aliases 
    echo "alias user-tool='ansible-playbook -i \"localhost,\" --connection=local /app/tests/run_user_tool.yml'" >> ~/.bashrc

    # Run ansible playbooks to setup expensify and mitmproxy
    ansible-playbook -i "localhost," --connection=local /app/tests/setup_expensify.yml
    ansible-playbook -i "localhost," --connection=local /app/tests/setup_mitmproxy.yml -vvvv

    # Set an environment variable to indicate that the setup is done
    echo "done" > /setup_done.txt
fi

# Start bash
tail -f /dev/null
