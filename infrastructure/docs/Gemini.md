# Gemini Code Assist Directives: Infrastructure (/infrastructure)

This document provides specific instructions for working within the /infrastructure directory. This is the blueprint for the entire operational environment of the Nautilus Trader ATS. All code and configurations here define how the system is deployed, scaled, secured, and monitored. Adherence to these directives is critical for building an enterprise-grade, resilient platform. These rules are in addition to the global directives in the root GEMINI.md file.

## 1\. Service Overview & Core Mission

The mission of the /infrastructure directory is to define the entire cloud-native foundation of the trading platform as code. Your primary goal is to create a fully automated, secure, and observable environment that supports a high-performance, multi-region, and fault-tolerant microservices architecture. This is not just about running the application; it's about ensuring it can withstand failure, scale under pressure, and meet stringent enterprise security and compliance standards.

## 2\. Key Technologies & Libraries (Mandatory)

You must use the following "Best-of-Breed" stack for all infrastructure-as-code development:

- **Containerization:** **Docker**. All applications and services must be defined via multi-stage, optimized Dockerfiles.
- **Orchestration:** **Kubernetes (K8s)**. This is the target runtime for all containerized services.
- **Package Management:** **Helm**. All Kubernetes applications must be packaged as versioned, configurable Helm charts.
- **Service Mesh:** **Istio**. This is mandatory for managing all inter-service communication, providing mTLS, traffic management, and observability.
- **API Gateway / Ingress:** **NGINX Ingress Controller**.
- **Observability Stack:**
  - **Prometheus:** For all metrics collection.
  - **Grafana:** For all dashboarding.
  - **Jaeger:** For all distributed tracing.
  - **Loki:** For all log aggregation.
- **CI/CD & GitOps:** **GitHub Actions** for CI, with a **GitOps** tool (like ArgoCD) for CD.
- **Infrastructure Provisioning:** **Terraform** for defining cloud resources (e.g., VPCs, Kubernetes clusters, managed databases).

## 3\. Core Responsibilities & Logic

This directory is responsible for defining and managing the following:

- **Container Images:** Create efficient and secure Dockerfiles for every microservice in the project.
- **Kubernetes Manifests & Helm Charts:** Define all Kubernetes resources (Deployments, Services, ConfigMaps, etc.) within modular and reusable Helm charts.
- **Service Mesh Configuration:** Implement Istio configurations for traffic routing (e.g., canary deployments), resilience (e.g., retries, circuit breakers), and security (e.g., AuthorizationPolicies).
- **CI/CD Pipelines:** Write all GitHub Actions workflows for building, testing, scanning, and deploying the application.
- **Observability Setup:** Define the configurations for deploying and integrating the entire observability stack (Prometheus, Grafana, etc.) to monitor the platform.
- **High Availability & Disaster Recovery:** The infrastructure code must support a multi-region deployment. You will be responsible for scripting backup, restore, and failover procedures (e.g., using Velero for Kubernetes backups).

## 4\. Integration Patterns & Data Flow (Strict)

- **Infrastructure as Code (IaC):** All infrastructure—from the cloud VPC to the application's Kubernetes configuration—**MUST** be defined as code and stored in this repository. Manual ("click-ops") changes to the production environment are strictly forbidden.
- **GitOps Workflow:** The state of the production environment must be driven by the state of the main branch in this repository. All changes must be deployed automatically via a GitOps controller that watches for commits.
- **Secret Management:** Services must not store secrets in their code or container images. All secrets (API keys, database passwords, TLS certificates) must be injected at runtime from a secure vault (like **HashiCorp Vault**) integrated with Kubernetes.

## 5\. Coding Standards & Patterns

- **Helm Charts:** Charts must be modular and follow best practices. All configurable values must be exposed in a values.yaml file with clear documentation.
- **Dockerfiles:** Use multi-stage builds to create lean, secure production images. Scan all images for vulnerabilities using a tool like Trivy as part of the CI pipeline.
- **Terraform:** Write modular and reusable Terraform code. The state file must be stored in a secure, remote backend (like an S3 bucket with locking).

## 6\. Testing Protocol

- **CI Pipeline Testing:** The CI pipeline must be the primary gate for quality. It must include:
  - **Linting:** All infrastructure code (YAML, Dockerfiles, Terraform) must be linted.
  - **Unit Testing:** Where applicable (e.g., testing Helm chart templates).
  - **Security Scanning:** All container images must be scanned for CVEs. All IaC code must be scanned for security misconfigurations.
- **Disaster Recovery Drills:** The infrastructure must be tested regularly via automated disaster recovery drills. The CI/CD pipeline should include a workflow to simulate a region failure and test the automated failover and recovery process, measuring the RTO (Recovery Time Objective) and RPO (Recovery Point Objective).

**Reference Documents for Nautilus Trader Development**

To ensure comprehensive guidance for each phase of the Nautilus Trader algorithmic trading system development, the Agent should refer to the following documents, located in the specified paths, for detailed requirements, designs, tasks, and other critical specifications:

- **System Requirements**:
  - **Document**: Comprehensive System Requirements
  - **Location**: /docs/complete_requirements.md
  - **Description**: Contains consolidated requirements across Phases 0-6, including user stories and acceptance criteria for all system functionalities.
- **System Designs**:
  - **Document**: Comprehensive System Designs
  - **Location**: /docs/complete_designs.md
  - **Description**: Provides detailed designs with high-level architectures, component breakdowns, and Mermaid diagrams for each phase.
- **System Tasks and Sub-Tasks**:
  - **Document**: Comprehensive System Tasks
  - **Location**: /docs/complete_tasks.md
  - **Description**: Lists over 450 detailed tasks and sub-tasks across all phases, serving as a roadmap for implementation.
- **System Architecture**:
  - **Document**: Comprehensive System Architecture
  - **Location**: /docs/comprehensive_system_architecture.md
  - **Description**: Details the system’s architecture, including overview, principles, components, data flows, technology stack, deployment, security, performance, integrations, and more.
- **Features, Phases, and Integration Strategy**:
  - **Document**: Features, Phases & Integration Strategy - Algorithmic Trading System
  - **Location**: /docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.md
  - **Description**: Outlines all features, phased development approach, and integration strategies for the Nautilus Trader platform.
- **Business Requirements**:
  - **Document**: Business Requirements Document (BRD) - Algorithmic Trading System
  - **Location**: /docs/02. Business Requirements Document (BRD) - Algorithmic Trading System.md
  - **Description**: Defines the business objectives, stakeholder needs, and high-level requirements driving the platform’s development.
- **Functional Requirements**:
  - **Document**: Functional Requirements Document (FRD) - Algorithmic Trading System
  - **Location**: /docs/03. Functional Requirements Document (FRD) - Algorithmic Trading System.md
  - **Description**: Specifies functional requirements, including user interactions, system behaviors, and operational workflows.
- **Product Requirements**:
  - **Document**: Product Requirements Document (PRD) - Algorithmic Trading System
  - **Location**: /docs/04. Product Requirements Document (PRD) - Algorithmic Trading System.md
  - **Description**: Details product-specific requirements, focusing on features, user experience, and market fit.
- **Functional Specification**:
  - **Document**: Functional Specification Document (FSD) - Algorithmic Trading System
  - **Location**: /docs/05. Functional Specification Document (FSD) - Algorithmic Trading System.md
  - **Description**: Provides detailed functional specifications, including system inputs, outputs, and processing logic.
- **Technical Specification**:
  - **Document**: Technical Specification Document (TSD) - Algorithmic Trading System
  - **Location**: /docs/06. Technical Specification Document (TSD) - Algorithmic Trading System.md
  - **Description**: Outlines technical specifications, including technology stack, APIs, and integration details.
- **System Design**:
  - **Document**: System Design Document (SDD) - Algorithmic Trading System
  - **Location**: /docs/07. System Design Document (SDD) - Algorithmic Trading System.md
  - **Description**: Describes the system’s design, including architecture patterns, component interactions, and deployment strategies.
- **Software Requirements Specification**:
  - **Document**: Software Requirements Specification (SRS) - Algorithmic Trading System
  - **Location**: /docs/08. Software Requirements Specification (SRS) - Algorithmic Trading System.md
  - **Description**: Combines functional and non-functional requirements for software development, ensuring alignment with business goals.
- **API Documentation**:
  - **Document**: API Documentation - Algorithmic Trading System
  - **Location**: /docs/09. API Documentation - Algorithmic Trading System.md
  - **Description**: Details all APIs (REST, GraphQL, WebSocket, gRPC) for system interactions, including endpoints, schemas, and usage examples.
- **Test Plan and Test Cases**:
  - **Document**: Comprehensive Test Plan and Test Cases - Algorithmic Trading System
  - **Location**: /docs/10. Comprehensive Test Plan and Test Cases - Algorithmic Trading System.md
  - **Description**: Provides a comprehensive test plan with detailed test cases for unit, integration, and end-to-end testing across all phases.
- **Configuration Management**:
  - **Document**: Configuration Management Plan - Algorithmic Trading System
  - **Location**: /docs/11. Configuration Management Plan - Algorithmic Trading System.md
  - **Description**: Defines processes for managing system configurations, version control, and dependency updates.
- **Data Flow**:
  - **Document**: Data Flow Document - Algorithmic Trading System
  - **Location**: /docs/12. Data Flow Document - Algorithmic Trading System.md
  - **Description**: Maps data flows across system components, including Kafka event streams, database interactions, and API calls.
- **Deployment Guide**:
  - **Document**: Deployment Guide - Algorithmic Trading System
  - **Location**: /docs/13. Deployment Guide - Algorithmic Trading System.md
  - **Description**: Provides step-by-step instructions for deploying the system, including Kubernetes, Helm, and Istio configurations.
- **User Documentation**:
  - **Document**: User Documentation - Algorithmic Trading System
  - **Location**: /docs/14. User Documentation - Algorithmic Trading System.md
  - **Description**: Offers user guides, tutorials, and FAQs for platform users, covering trading, strategy building, and marketplace interactions.

**Usage Instructions:**

- The above-mentioned documents must be referenced for each phase’s implementation, ensuring alignment with requirements, designs, and tasks.
- Use /docs/complete_requirements.md, /docs/complete_designs.md, and /docs/complete_tasks.md as primary references for phase-specific details.
- Cross-reference /docs/comprehensive_system_architecture.md for architectural guidance and /docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.md for overarching feature and integration strategies.
- For specific documentation needs (e.g., APIs, testing, deployment), refer to the respective specialized documents.
- Maintain traceability by linking code, configurations, and tests to document IDs and requirements (e.g., // @REFERENCE: req ID, doc path).
