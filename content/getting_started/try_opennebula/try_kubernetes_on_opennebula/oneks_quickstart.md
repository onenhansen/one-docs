---
title: "Elastic Kubernetes with OneKS Quickstart Guide"
linkTitle: "OneKS Quickstart"
date: "2026-06-09"
type: docs
description:
---

In this tutorial, we will use OpenNebula's Elastic Kubernetes service — OneKS — to rapidly deploy a K8s Cluster and then deploy an application on it. 

## Before Starting

In order to complete this tutorial you need to have access to the Enterprise Edition of OpenNebula and have OpenNebula version 7.2.1 installed.

* [Install the OpenNebula Front-end]({{% relref "software/installation_process/frontend_installation/frontend_install/" %}})
* Install an OpenNebula Cluster node:
    * Automatically with OneForm

## Install miniONE

```shell
wget https://github.com/OpenNebula/minione/releases/download/v7.2.0.1/minione
```

```shell
chmod +x minione
```

```shell
./minione --enterprize uname:token
```

```shell
nano /var/lib/one/remotes/etc/vnm/OpenNebulaNetwork.conf
```

Edit Tproxy lines:

```default
################################################################################
# TProxy / OneGate Options
################################################################################

...

# The simplest example of an OneGate proxy config applied to all VNETs:
:tproxy:
- :service_port: 5030
  :remote_addr: 127.0.0.1 # Loopback address
  :remote_port: 5030
- :remote_addr: 127.0.0.1 # Loopback address
  :remote_port: 2633
  :service_port: 2633
```

Install OneKS

```shell
apt-get install opennebula-ks
```

Start the OneKS service

```shell
systemctl start opennebula-ks
```

### Create a Private Virtual Network

Create a new virtual network, name it private, in the Configuration tab choose "User private host networking or a user-defined bridge". 

In Addresses tab, add address range with a range of 100.

### Install Kubectl on the Front-end Command Line

Install Kubectl on the Front-

```shell
curl -LO "https://dl.k8s.io/release/$(curl -L -s \
https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
```

Install:

```shell
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

Check install:

```shell
kubectl version --client
```

Example output:

```default
Client Version: v1.36.1
Kustomize Version: v5.8.1
```

## Create a K8s Cluster

From the left-hand navigation menu in Sunstone, go to **Kubernetes -> K8S Clusters**:

{{< image path="/images/oneks/light/create_k8s_cluster_1.png"
          pathDark="/images/oneks/dark/create_k8s_cluster_1.png"
alt="OneKS create Cluster step 1" align="center" width="90%" mb="20px" >}}

In the **General** step, provide the basic K8s Cluster information. Enter a K8s Cluster name and, optionally, a description.

{{< image path="/images/oneks/light/create_k8s_cluster_2.png" 
          pathDark="/images/oneks/dark/create_k8s_cluster_2.png"
alt="OneKS create K8s Cluster general" align="center" width="90%" mb="20px" >}}

In **Select a Public Virtual Network**, select the `vnet` Virtual Network that was automatically set up during the miniONE installation. The public network acts as the gateway to the Internet and is used by the K8s Cluster to expose external access where required.

{{< image path="/images/oneks/light/oneks_qs_public_network.png" 
          pathDark="/images/oneks/dark/oneks_qs_public_network.png"
alt="OneKS create K8s Cluster public network" align="center" width="90%" mb="20px" >}}

In **Select a Private Virtual Network**, select the private Virtual Network that you created earlier. This network provides isolation from the public Internet and is used for communication between the K8s Cluster nodes.

{{< image path="/images/oneks/light/oneks_qs_private_network.png" 
          pathDark="/images/oneks/dark/oneks_qs_private_network.png"
alt="OneKS create K8s Cluster public network" align="center" width="90%" mb="20px" >}}

In **Kubernetes Version**, select the Kubernetes version you intend to deploy. Only the versions available in the environment are shown.

{{< image path="/images/oneks/light/create_k8s_cluster_version.png"
          pathDark="/images/oneks/dark/create_k8s_cluster_version.png"
alt="OneKS create K8s Cluster choose k8s version" align="center" width="90%" mb="20px" >}}

In **Flavours**, select the control-plane flavour for the K8s Cluster. The flavour defines the control-plane deployment model and the resources used by the control-plane nodes.

Available options include:

* **Single-node Control Plane**: Deploys one control-plane node. Suitable for development, evaluation, and non-critical workloads.  
* **Highly Available Control Plane**: Deploys three control-plane nodes with built-in redundancy. Suitable for production or environments that require higher availability.

{{< image path="/images/oneks/light/create_k8s_cluster_flavours.png" 
          pathDark="/images/oneks/dark/create_k8s_cluster_flavours.png"
alt="OneKS create K8s Cluster choose k8s version" align="center" width="90%" mb="20px" >}}

In **User Inputs**, review the remaining user input parameters required by the selected K8s Cluster configuration.

After completing the required fields, finish the wizard to start K8s Cluster creation. You will be redirected to the **Kubernetes Logs** view, where you can monitor the provisioning process.

During provisioning, the K8s Cluster initially appears with a `CREATING` or `PROVISIONING` status. The control-plane nodes are provisioned according to the selected flavour. This process typically takes several minutes.

{{< image path="/images/oneks/light/k8s_logs_creating.png"
          pathDark="/images/oneks/dark/k8s_logs_creating.png"
alt="OneKS create K8s Cluster choose k8s version" align="center" width="90%" mb="20px" >}}

Continue waiting until the K8s Cluster reaches the `RUNNING` state in the Sunstone **Kubernetes Logs** view.

{{< image path="/images/oneks/light/create_k8s_logs_running.png" 
          pathDark="/images/oneks/dark/create_k8s_logs_running.png" 
alt="OneKS create K8s Cluster choose k8s version" align="center" width="90%" mb="20px" >}}

You can verify that the K8s Cluster is running using the `onevm list` command on the Front-end command line. You should still see the two newly created VMs, one for the virtual router and one for the control plane. The seed VM will terminate upon completion of the process:

```default
ID USER     GROUP    NAME                     STAT  CPU     MEM HOST                                             TIME
 2 oneadmin oneadmin test-cluster-nmhhb       runn    2      4G ubuntu2204-kvm-ssh-ks-7-2-f1wvx-2.test       0d 03h26
 1 oneadmin oneadmin vr-test-cluster-cp-0     runn    1    512M ubuntu2204-kvm-ssh-ks-7-2-f1wvx-1.test       0d 03h26
```