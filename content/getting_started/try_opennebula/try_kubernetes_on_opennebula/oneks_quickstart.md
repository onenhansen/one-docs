---
title: "Quickstart: Elastic Kubernetes on OpenNebula with OneKS (EE)"
linkTitle: "OneKS Quickstart Guide (EE)"
date: "2025-02-17"
description:
categories: [Learning, Evaluation, Deployment, Introduction]
pageintoc: "23"
tags: ['Quick Start', Kubernetes, Tutorial, OneKE]
type: docs
weight: "7"
---

## Overview

OneKS provides Elastic Kubernetes-as-a-Service on OpenNebula. It offers a streamlined, structured way to create, access, operate, upgrade, recover, and deprovision Kubernetes Clusters (K8s Clusters) by combining a user-facing service layer with Cluster API-based infrastructure provisioning through CAPONE, the Cluster API provider for OpenNebula. This quickstart guide leads you through the steps to try OneKS with a simple example deployment.

OneKS is an Enterprise Extension available as part of an Enterprise Subscription. Please see the [documentation about Enterprise Subscriptions and Extensions]({{% relref "software/release_information/release_notes/editions/" %}}) for more information or visit the [OpenNebula website](https://opennebula.io/enterprise-services/#subscriptions) for information about acquiring an Enterprise Subscription. 

## Installation

OneKS requires a full OpenNebula Front-end installation with at least one Cluster node installed using the Enterprise Edition package repositories (OneKS is not supported by miniONE). Proceed with the following steps (in the given order) to install OpenNebula Enterprise Edition and OneKS.

### 1. Install an OpenNebula Front-end

The Front-end serves as the control plane of an OpenNebula cloud deployment. It manages all aspects of an OpenNebula-managed cloud including K8s Clusters deployed with OneKS. Follow these steps (in the given order) to deploy and OpenNebula Front-end:

* Ensure that your hardware meets the [requirements]({{% relref "software/installation_process/frontend_installation/overview/#requirements" %}})
* [Install a database]({{% relref "software/installation_process/frontend_installation/database/" %}}) to persist the cloud state
* [Set up the Enterprise Edition repositories]({{% relref "software/installation_process/frontend_installation/opennebula_repository_configuration_ee/" %}})
* [Install an OpenNebula Front-end]({{% relref "software/installation_process/frontend_installation/frontend_install/" %}})

### 2. Install an OpenNebula Cluster

An OpenNebula Cluster is a logical grouping of Hosts, datastores and Virtual Networks that provide compute capacity for cloud workloads. After deploying an OpenNebula Front-end, you must deploy at least one OpenNebula Cluster to handle the guest workload of a K8s Cluster. There are 2 options to deploy an OpenNebula Cluster to host a K8s Cluster:

* [Automated Cluster deployment with OneForm]({{% relref "software/installation_process/cluster_installation/automated/" %}})
* [Manual Cluster installation with KVM]({{% relref "software/installation_process/cluster_installation/kvm_node_installation/" %}})

## Configuration

Before deploying a K8s Cluster, it is necessary to ensure that the OpenNebula cloud is properly configured for OneKS. Refer to the [OneKS Basic Configuration Guide]({{% relref "platform_services/oneks/getting_started/basic_configuration/" %}}) to prepare your OpenNebula cloud for OneKS.

## Deploy a K8s Cluster with OneKS

Once you have deployed a Front-end and at least one OpenNebula Cluster and completed configuration, you are ready to try deploying a K8s Cluster with OneKS. Follow the steps in the [OneKS Quick-start Guide]({{% relref "platform_services/oneks/getting_started/quick_start/" %}}) to deploy your first K8s Cluster. 

## Next Steps

After learning how to deploy a K8s Cluster with OneKS, the next step is learning to manage, monitor, and troubleshoot Cluster lifecycles, refer to the following guides for more information:

* [K8s Cluster Lifecycle Management]({{% relref "platform_services/oneks/management/k8s_cluster_lifecycle_management/" %}})
* [Monitoring and Troubleshooting]({{% relref "platform_services/oneks/management/monitoring_and_troubleshooting/" %}})
* [Configuration]({{% relref "platform_services/oneks/management/configuration/" %}})
* [Profiles Customization]({{% relref "platform_services/oneks/management/customizing_specs/" %}})

OneKS is can be managed through 3 interfaces: the Sunstone web UI, CLI and REST API. Refer to the following references for more details: 

* [OneKS REST API]({{% relref "platform_services/oneks/references/oneks_api/" %}})
* [OneKS CLI]({{% relref "platform_services/oneks/references/oneks_cli/" %}})
* [Service Architecture]({{% relref "platform_services/oneks/references/architecture/" %}})












