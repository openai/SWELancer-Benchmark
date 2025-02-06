Swarm server has 4 parts

3 programs run on the api server. This is a single VM in azure where @evanmays deploy's manually

* `server.py` has POST /claim, POST /kill_machines, and GET /status binded to port 80. It scales to arbitrary processes.

* `autoscale.py` spins up and down azure VMs in groups (scalesets)

* `state.py` is our own little knock-off redis database. It stores the state of all the VMs. server and autoscale communicate with state.py over ZMQ

The fourth part of swarm server is the code that runs on the wokrers. This is in the `worker` folder
