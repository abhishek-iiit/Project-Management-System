#!/bin/bash

# BugsTracker Deployment Script
# This script deploys the application to Kubernetes cluster

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
NAMESPACE="bugstracker-${ENVIRONMENT}"
DOCKER_REGISTRY="ghcr.io"
IMAGE_TAG=${2:-latest}

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check if context is set
    if ! kubectl config current-context &> /dev/null; then
        log_error "kubectl context is not set"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

create_namespace() {
    log_info "Creating namespace ${NAMESPACE}..."
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
}

create_secrets() {
    log_info "Creating secrets..."

    # Check if secrets already exist
    if kubectl get secret backend-secret -n ${NAMESPACE} &> /dev/null; then
        log_warn "Secrets already exist. Skipping creation."
        log_warn "If you need to update secrets, delete them first or update manually."
    else
        log_error "Secrets not found. Please create them manually using:"
        log_error "kubectl create secret generic backend-secret --from-literal=SECRET_KEY='...' -n ${NAMESPACE}"
        exit 1
    fi
}

deploy_infrastructure() {
    log_info "Deploying infrastructure components..."

    # Deploy PostgreSQL
    log_info "Deploying PostgreSQL..."
    kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml -n ${NAMESPACE}

    # Deploy Redis
    log_info "Deploying Redis..."
    kubectl apply -f infrastructure/kubernetes/redis-deployment.yaml -n ${NAMESPACE}

    # Deploy Elasticsearch
    log_info "Deploying Elasticsearch..."
    kubectl apply -f infrastructure/kubernetes/elasticsearch-statefulset.yaml -n ${NAMESPACE}

    # Wait for infrastructure to be ready
    log_info "Waiting for infrastructure to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=elasticsearch -n ${NAMESPACE} --timeout=600s
}

deploy_application() {
    log_info "Deploying application..."

    # Apply ConfigMap
    log_info "Applying ConfigMap..."
    kubectl apply -f infrastructure/kubernetes/configmaps/backend-config.yaml -n ${NAMESPACE}

    # Update image tags
    log_info "Updating image tags to ${IMAGE_TAG}..."

    # Deploy backend
    log_info "Deploying backend..."
    kubectl apply -f infrastructure/kubernetes/backend-deployment.yaml -n ${NAMESPACE}

    # Deploy Celery workers
    log_info "Deploying Celery workers..."
    kubectl apply -f infrastructure/kubernetes/celery-deployment.yaml -n ${NAMESPACE}

    # Apply HPA
    log_info "Applying HorizontalPodAutoscaler..."
    kubectl apply -f infrastructure/kubernetes/hpa.yaml -n ${NAMESPACE}

    # Wait for deployments
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available deployment/backend-green -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=available deployment/celery-worker -n ${NAMESPACE} --timeout=300s
}

run_migrations() {
    log_info "Running database migrations..."

    # Get first backend pod
    BACKEND_POD=$(kubectl get pod -n ${NAMESPACE} -l app=backend,version=green -o jsonpath='{.items[0].metadata.name}')

    if [ -z "$BACKEND_POD" ]; then
        log_error "No backend pod found"
        exit 1
    fi

    log_info "Running migrations on pod ${BACKEND_POD}..."
    kubectl exec -n ${NAMESPACE} ${BACKEND_POD} -- python manage.py migrate --noinput

    log_info "Migrations completed"
}

collect_static() {
    log_info "Collecting static files..."

    BACKEND_POD=$(kubectl get pod -n ${NAMESPACE} -l app=backend,version=green -o jsonpath='{.items[0].metadata.name}')

    kubectl exec -n ${NAMESPACE} ${BACKEND_POD} -- python manage.py collectstatic --noinput

    log_info "Static files collected"
}

deploy_ingress() {
    log_info "Deploying ingress..."
    kubectl apply -f infrastructure/kubernetes/nginx-ingress.yaml -n ${NAMESPACE}
}

health_check() {
    log_info "Running health checks..."

    # Get service URL
    if [ "$ENVIRONMENT" = "production" ]; then
        SERVICE_URL="https://api.bugstracker.com"
    else
        SERVICE_URL="https://staging-api.bugstracker.com"
    fi

    # Wait a bit for the service to be ready
    sleep 30

    # Check health endpoint
    log_info "Checking ${SERVICE_URL}/health/"

    if curl -f -s ${SERVICE_URL}/health/ > /dev/null; then
        log_info "Health check passed!"
    else
        log_error "Health check failed!"
        exit 1
    fi
}

show_status() {
    log_info "Deployment Status:"
    echo ""
    kubectl get pods -n ${NAMESPACE}
    echo ""
    kubectl get services -n ${NAMESPACE}
    echo ""
    kubectl get ingress -n ${NAMESPACE}
}

rollback() {
    log_error "Deployment failed. Rolling back..."

    # Rollback backend
    kubectl rollout undo deployment/backend-green -n ${NAMESPACE}

    # Rollback celery
    kubectl rollout undo deployment/celery-worker -n ${NAMESPACE}

    log_info "Rollback completed"
}

# Main deployment flow
main() {
    log_info "Starting deployment to ${ENVIRONMENT} environment..."
    log_info "Image tag: ${IMAGE_TAG}"

    # Set error trap
    trap 'log_error "Deployment failed at line $LINENO"' ERR

    check_prerequisites
    create_namespace
    create_secrets

    # Deploy components
    deploy_infrastructure
    deploy_application

    # Run post-deployment tasks
    run_migrations
    collect_static
    deploy_ingress

    # Verify deployment
    health_check
    show_status

    log_info "Deployment completed successfully!"
    log_info "Application is now running at:"

    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "  https://api.bugstracker.com"
    else
        log_info "  https://staging-api.bugstracker.com"
    fi
}

# Run main function
main "$@"
