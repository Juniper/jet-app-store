# Container Monitoring using JET and YANG

The objective of this project is to illustrate how to use the JET APIs on Junos devices to build a custom application. The project will demonstrate:

- Running Python applications with third party Python libraries onbox
- Collect operational state information from Junos using JET MGMT API
- Extend the Junos CLI to provide custom operation mode commands
- Publish application output similar to the output from a Junos operations mode command
- Demonstrate the ability to use XML RPC for the newly created operation mode command

# Use Case Overview

This project addresses the use case where Network operators need the visibility into location of containers with respect to the network for troubleshooting. On any given network device, Network operators can run an operations mode command to identify the containers and the nodes connected to that switch. This information can be obtained either from the CLI or queried remotely using XML RPC.

### Docker Components

#### Docker Swarm

Docker Swarm is a clustering and scheduling tool for Docker containers. Swarm provides the ability to manage multiple Docker nodes as a single virtual system. Docker swarm provides the ability to manage hundreds of containers across multiple Docker nodes with features like load balancing and resource allocation based on utilization.

#### Docker Node

A **node** is an instance of the Docker engine participating in the swarm. A node is an instance of the Docker engine participating in the swarm. You can also think of this as a Docker node. You can run one or more nodes on a single physical computer or cloud server, but production swarm deployments typically include Docker nodes distributed across multiple physical and cloud machines.

To deploy your application to a swarm, you submit a service definition to a manager node. The manager node dispatches units of work called tasks to worker nodes.

Manager nodes also perform the orchestration and cluster management functions required to maintain the desired state of the swarm. Manager nodes elect a single leader to conduct orchestration tasks.

Worker nodes receive and execute tasks dispatched from manager nodes. By default manager nodes also run services as worker nodes, but you can configure them to run manager tasks exclusively and be manager-only nodes. An agent runs on each worker node and reports on the tasks assigned to it. The worker node notifies the manager node of the current state of its assigned tasks so that the manager can maintain the desired state of each worker.

Please refer to Docker documentation for details about the Docker components.

[https://docs.docker.com/engine/swarm/key-concepts/](https://docs.docker.com/engine/swarm/key-concepts/)



### QFX Switches

This could be any of the Junos QFX switches that is running software versions 17.1 or later.

## UseCase Workflow

Network operator trying to identify the containers that are attached to a particular switch can run the custom extended operation mode CLI command &quot;show docker containers&quot; on the switch. This custom command was created using the YANG infrastructure in Junos. Executing this command will trigger the cmonitor.py script.

The cmonitor.py script running on the box performs the following tasks

- Query the QFX switch using JET APIs to identify the LLDP neighbors on the switch
- Use the docker.py modules to query the Docker Swarm manager node to get the list of containers and the worker nodes on which these containers are located
- Match the LLDP neighbor information from QFX switches with the worker node information received from the Swarm manager node
- Identify the list of containers that are attached directly to this QFX switch
- The script will render the collected information to the screen like a regular Junos show command output

## Step1: Enable Extension Services on the QFX Switches
set system scripts language python

set system services xnm-clear-text connection-limit 75
set system services xnm-clear-text rate-limit 150

set system services extension-service request-response grpc clear-text address 0.0.0.0
set system services extension-service request-response grpc clear-text port 32767

set system extensions extension-service application file demo.py

## Step2: Set Loopback IP and Enable LLDP on the QFX switches
set interfaces lo0 unit 0 family inet address 127.0.0.1/32
set protocols lldp interface all

## Step3: Copy the necessary JET API modules for this use case
Copy “authentication_service_pb2.py”, “authentication_service_pb2_grpc.py”, “mgd_service_pb2.py”, “mgd_service_pb2_grpc.py” from the /py/ directory to /var/db/scripts/action on the QFX switches

## Step4: Import the third party library. In this case “docker.py” to QFX5100
-	On any linux server with Python, install the docker-py module and dependencies 
-	On the linux server change to the directory “/usr/local/lib/python2.7/dist-packages”
-	Copy the folders for “backports”, “certifi”, “cffi”, “chardet”, “cryptography”, “docker”, “dockerpycreds”, “idna”, “ipaddress.py”, “requests”, “six.py”, “urllib3”, and “websocket” to /var/db/scripts/action on the QFX switches

## Step5: Copy the necessary files for extending the CLI.
From git clone, copy the py/cmonitor.py script, rpc-docker-containers.yang, junos-extension.yang and junos-extension-odl.yang modules to /var/tmp-docker-jet on the QFX switches.


## Step6: Extend the Operational mode CLI using the YANG support infrastructure in the QFX switches
On the operations mode CLI of the QFX switches, execute the following  
request system yang add package docker-rpc module [/var/tmp/docker-jet/rpc-docker-containers.yang /var/tmp/docker-jet/junos-extension.yang /var/tmp/docker-jet/junos-extension-odl.yang] action-script /var/tmp/docker-jet/cmonitor.py

# Verification
Verification on QFX switch
1.	Verify that the Docker worker nodes have been discovered through LLDP.  
user@host> show lldp neighbors  

2.	Verify that the switch is able to show the containers on the attached worker nodes.  
user@host> show docker containers 

3.	Verify that the YANG module and the action script are configured properly.  
user@host> show system yang package 


