# BugsTracker Deployment Guide

This guide covers deploying BugsTracker to a Kubernetes cluster in both staging and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Blue-Green Deployment](#blue-green-deployment)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Docker** (v20.10+)
- **kubectl** (v1.28+)
- **Kubernetes cluster** (v1.28+)
  - Recommended: GKE, EKS, or AKS
  - Minimum 3 nodes (4 vCPU, 16GB RAM each)
- **Helm** (v3.12+) - for installing monitoring stack
- **Git** - for version control

### Cluster Requirements

- **Storage Class**: Standard persistent volumes
- **Ingress Controller**: NGINX Ingress Controller
- **Cert Manager**: For SSL/TLS certificates (optional but recommended)
- **Metrics Server**: For HPA functionality

### Access Requirements

- Kubernetes cluster admin access
- Docker registry access (GitHub Container Registry)
- Domain names configured:
  - Production: `api.bugstracker.com`
  - Staging: `staging-api.bugstracker.com`

## Local Development Setup

### Using Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/bugstracker.git
   cd bugstracker
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

3. **Start all services:**
   ```bash
   cd infrastructure/docker
   docker-compose up -d
   ```

4. **Run migrations:**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Create superuser:**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Access the application:**
   - API: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - Flower (Celery monitoring): http://localhost:5555

7. **Stop services:**
   ```bash
   docker-compose down
   ```

### Running Tests

```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=apps --cov-report=html

# Run specific test
docker-compose exec backend pytest apps/issues/tests/test_models.py
```

## Staging Deployment

### Step 1: Build and Push Docker Images

The CI/CD pipeline automatically builds and pushes images on every commit to `main` branch.

Manual build:
```bash
# Build backend
docker build -f infrastructure/docker/Dockerfile.backend -t ghcr.io/yourusername/bugstracker-backend:staging .

# Build celery
docker build -f infrastructure/docker/Dockerfile.celery -t ghcr.io/yourusername/bugstracker-celery:staging .

# Push to registry
docker push ghcr.io/yourusername/bugstracker-backend:staging
docker push ghcr.io/yourusername/bugstracker-celery:staging
```

### Step 2: Create Kubernetes Secrets

```bash
# Create namespace
kubectl create namespace bugstracker-staging

# PostgreSQL credentials
kubectl create secret generic postgres-secret \
  --from-literal=database='bugstracker' \
  --from-literal=username='postgres' \
  --from-literal=password='CHANGE_ME_STRONG_PASSWORD' \
  -n bugstracker-staging

# Redis password
kubectl create secret generic redis-secret \
  --from-literal=password='CHANGE_ME_REDIS_PASSWORD' \
  -n bugstracker-staging

# Backend secrets
kubectl create secret generic backend-secret \
  --from-literal=SECRET_KEY='CHANGE_ME_DJANGO_SECRET_KEY' \
  --from-literal=DB_PASSWORD='CHANGE_ME_STRONG_PASSWORD' \
  --from-literal=EMAIL_HOST_PASSWORD='your-email-password' \
  --from-literal=SENTRY_DSN='your-sentry-dsn' \
  -n bugstracker-staging

# Flower credentials
kubectl create secret generic flower-secret \
  --from-literal=username='admin' \
  --from-literal=password='CHANGE_ME_FLOWER_PASSWORD' \
  -n bugstracker-staging
```

### Step 3: Deploy Infrastructure

```bash
# Deploy PostgreSQL
kubectl apply -f infrastructure/kubernetes/postgres-statefulset.yaml -n bugstracker-staging

# Deploy Redis
kubectl apply -f infrastructure/kubernetes/redis-deployment.yaml -n bugstracker-staging

# Deploy Elasticsearch
kubectl apply -f infrastructure/kubernetes/elasticsearch-statefulset.yaml -n bugstracker-staging

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n bugstracker-staging --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n bugstracker-staging --timeout=300s
kubectl wait --for=condition=ready pod -l app=elasticsearch -n bugstracker-staging --timeout=600s
```

### Step 4: Deploy Application

```bash
# Apply ConfigMap
kubectl apply -f infrastructure/kubernetes/configmaps/backend-config.yaml -n bugstracker-staging

# Deploy backend
kubectl apply -f infrastructure/kubernetes/backend-deployment.yaml -n bugstracker-staging

# Deploy Celery workers
kubectl apply -f infrastructure/kubernetes/celery-deployment.yaml -n bugstracker-staging

# Apply HPA
kubectl apply -f infrastructure/kubernetes/hpa.yaml -n bugstracker-staging

# Deploy ingress
kubectl apply -f infrastructure/kubernetes/nginx-ingress.yaml -n bugstracker-staging
```

### Step 5: Run Migrations

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pod -n bugstracker-staging -l app=backend,version=green -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -n bugstracker-staging $BACKEND_POD -- python manage.py migrate

# Collect static files
kubectl exec -n bugstracker-staging $BACKEND_POD -- python manage.py collectstatic --noinput

# Create superuser (optional)
kubectl exec -it -n bugstracker-staging $BACKEND_POD -- python manage.py createsuperuser
```

### Step 6: Verify Deployment

```bash
# Check pod status
kubectl get pods -n bugstracker-staging

# Check logs
kubectl logs -f deployment/backend-green -n bugstracker-staging

# Check ingress
kubectl get ingress -n bugstracker-staging

# Test health endpoint
curl https://staging-api.bugstracker.com/health/
```

## Production Deployment

Production deployment follows the same steps as staging, but with additional safety measures:

### Using the Deployment Script

```bash
# Deploy to production
./scripts/deploy.sh production v1.0.0

# The script will:
# 1. Check prerequisites
# 2. Create namespace
# 3. Verify secrets exist
# 4. Deploy infrastructure
# 5. Deploy application
# 6. Run migrations
# 7. Collect static files
# 8. Deploy ingress
# 9. Run health checks
# 10. Show deployment status
```

### Manual Production Deployment

Same as staging, but use `bugstracker-production` namespace:

```bash
kubectl create namespace bugstracker-production

# Create secrets (same as staging but in production namespace)
kubectl create secret generic postgres-secret \
  --from-literal=database='bugstracker' \
  --from-literal=username='postgres' \
  --from-literal=password='PRODUCTION_PASSWORD' \
  -n bugstracker-production

# ... (repeat for other secrets)

# Deploy components
kubectl apply -f infrastructure/kubernetes/ -n bugstracker-production
```

## Blue-Green Deployment

BugsTracker uses blue-green deployment strategy for zero-downtime deployments.

### Architecture

- **Blue deployment**: Currently serving traffic
- **Green deployment**: New version being deployed
- **Service**: Routes traffic to blue or green based on selector

### Deployment Process

1. **Deploy new version to green:**
   ```bash
   # Update green deployment with new image
   kubectl set image deployment/backend-green \
     backend=ghcr.io/yourusername/bugstracker-backend:v1.1.0 \
     -n bugstracker-production

   # Wait for rollout
   kubectl rollout status deployment/backend-green -n bugstracker-production
   ```

2. **Run migrations on green:**
   ```bash
   GREEN_POD=$(kubectl get pod -n bugstracker-production -l app=backend,version=green -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n bugstracker-production $GREEN_POD -- python manage.py migrate
   ```

3. **Health check green deployment:**
   ```bash
   # Test green deployment internally
   kubectl exec -n bugstracker-production $GREEN_POD -- curl -f http://localhost:8000/health/
   ```

4. **Switch traffic to green:**
   ```bash
   # Update service selector to point to green
   kubectl patch service backend -n bugstracker-production \
     -p '{"spec":{"selector":{"version":"green"}}}'
   ```

5. **Monitor for issues:**
   ```bash
   # Monitor logs and metrics for 5-10 minutes
   kubectl logs -f deployment/backend-green -n bugstracker-production

   # Check error rates in Prometheus/Grafana
   ```

6. **If successful, scale down blue:**
   ```bash
   kubectl scale deployment/backend-blue --replicas=0 -n bugstracker-production
   ```

7. **If rollback needed:**
   ```bash
   # Switch traffic back to blue
   kubectl patch service backend -n bugstracker-production \
     -p '{"spec":{"selector":{"version":"blue"}}}'

   # Scale up blue if needed
   kubectl scale deployment/backend-blue --replicas=3 -n bugstracker-production
   ```

8. **Prepare for next deployment:**
   ```bash
   # Blue becomes the new green (swap roles)
   # Update blue deployment with green's image for next deployment cycle
   ```

## Monitoring and Logging

### Prometheus + Grafana Setup

1. **Install Prometheus Operator:**
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update

   helm install prometheus prometheus-community/kube-prometheus-stack \
     --namespace monitoring \
     --create-namespace \
     -f infrastructure/monitoring/prometheus-values.yaml
   ```

2. **Access Grafana:**
   ```bash
   kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
   # Open http://localhost:3000
   # Default credentials: admin / prom-operator
   ```

3. **Import dashboards:**
   - Django dashboard: ID 12900
   - Kubernetes cluster: ID 7249
   - PostgreSQL: ID 9628
   - Redis: ID 11835

### Application Metrics

BugsTracker exposes metrics at `/metrics` endpoint:

```python
# Custom metrics exposed:
- http_requests_total
- http_request_duration_seconds
- django_db_connections_used
- django_db_connections_total
- celery_tasks_total
- celery_task_duration_seconds
- celery_queue_length
```

### Alerting

Alerts are configured in `infrastructure/monitoring/alerts/`:

- **Critical alerts**: Sent to PagerDuty/Slack immediately
- **Warning alerts**: Sent to Slack
- **Info alerts**: Logged only

Configure Alertmanager:
```bash
kubectl apply -f infrastructure/monitoring/alertmanager-config.yaml -n monitoring
```

### Log Aggregation (ELK Stack)

1. **Install Elasticsearch, Logstash, Kibana:**
   ```bash
   helm repo add elastic https://helm.elastic.co
   helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
   helm install kibana elastic/kibana -n logging
   helm install filebeat elastic/filebeat -n logging
   ```

2. **Configure Filebeat to collect logs:**
   ```yaml
   # filebeat-config.yaml
   filebeat.inputs:
   - type: container
     paths:
       - /var/log/containers/bugstracker*.log
   ```

3. **Access Kibana:**
   ```bash
   kubectl port-forward -n logging svc/kibana-kibana 5601:5601
   # Open http://localhost:5601
   ```

### Sentry Integration

Configure Sentry DSN in backend-secret for error tracking:

```bash
kubectl create secret generic backend-secret \
  --from-literal=SENTRY_DSN='https://your-sentry-dsn@sentry.io/project-id' \
  -n bugstracker-production
```

## Troubleshooting

### Common Issues

#### 1. Pods not starting

```bash
# Check pod status
kubectl get pods -n bugstracker-production

# Check pod events
kubectl describe pod <pod-name> -n bugstracker-production

# Check logs
kubectl logs <pod-name> -n bugstracker-production

# Common causes:
# - Image pull errors (check image registry credentials)
# - Resource limits (check node capacity)
# - Secrets missing (verify all secrets created)
```

#### 2. Database connection errors

```bash
# Check PostgreSQL pod
kubectl get pod -l app=postgres -n bugstracker-production

# Check PostgreSQL logs
kubectl logs -l app=postgres -n bugstracker-production

# Test connection from backend pod
kubectl exec -it <backend-pod> -n bugstracker-production -- \
  psql -h postgres -U postgres -d bugstracker

# Verify secrets
kubectl get secret postgres-secret -n bugstracker-production -o yaml
```

#### 3. Migrations failing

```bash
# Check migration status
kubectl exec <backend-pod> -n bugstracker-production -- \
  python manage.py showmigrations

# Run migrations manually
kubectl exec <backend-pod> -n bugstracker-production -- \
  python manage.py migrate --fake-initial

# Rollback specific migration
kubectl exec <backend-pod> -n bugstracker-production -- \
  python manage.py migrate <app_name> <migration_name>
```

#### 4. High memory usage

```bash
# Check resource usage
kubectl top pods -n bugstracker-production

# Check HPA status
kubectl get hpa -n bugstracker-production

# Increase resource limits if needed
kubectl edit deployment backend-green -n bugstracker-production
```

#### 5. Elasticsearch cluster not forming

```bash
# Check all Elasticsearch pods
kubectl get pods -l app=elasticsearch -n bugstracker-production

# Check cluster health
kubectl exec elasticsearch-0 -n bugstracker-production -- \
  curl http://localhost:9200/_cluster/health?pretty

# Check discovery logs
kubectl logs elasticsearch-0 -n bugstracker-production | grep discovery

# Common fix: Ensure all pods can communicate
kubectl exec elasticsearch-0 -n bugstracker-production -- \
  curl http://elasticsearch-1.elasticsearch:9200
```

### Health Checks

```bash
# API health
curl https://api.bugstracker.com/health/

# Database health
kubectl exec -n bugstracker-production postgres-0 -- pg_isready

# Redis health
kubectl exec -n bugstracker-production <redis-pod> -- redis-cli ping

# Elasticsearch health
kubectl exec -n bugstracker-production elasticsearch-0 -- \
  curl http://localhost:9200/_cluster/health
```

### Performance Debugging

```bash
# Enable Django debug toolbar (development only!)
kubectl exec <backend-pod> -n bugstracker-staging -- \
  python manage.py shell -c "from django.conf import settings; print(settings.DEBUG)"

# Check slow queries
kubectl exec postgres-0 -n bugstracker-production -- \
  psql -U postgres -d bugstracker -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check Celery queue length
kubectl exec <celery-pod> -n bugstracker-production -- \
  celery -A config inspect active_queues
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend-green -n bugstracker-production

# Rollback to specific revision
kubectl rollout undo deployment/backend-green --to-revision=2 -n bugstracker-production

# Check rollout history
kubectl rollout history deployment/backend-green -n bugstracker-production
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment/backend-green --replicas=10 -n bugstracker-production

# Scale Celery workers
kubectl scale deployment/celery-worker --replicas=5 -n bugstracker-production
```

### Auto Scaling

HPA is configured for automatic scaling based on CPU/memory:

```bash
# Check HPA status
kubectl get hpa -n bugstracker-production

# Describe HPA
kubectl describe hpa backend-hpa -n bugstracker-production
```

## Backup and Restore

### Database Backup

```bash
# Create backup
kubectl exec postgres-0 -n bugstracker-production -- \
  pg_dump -U postgres bugstracker > backup-$(date +%Y%m%d-%H%M%S).sql

# Automated backup (cron job)
kubectl apply -f infrastructure/kubernetes/backup-cronjob.yaml
```

### Restore Database

```bash
# Copy backup to pod
kubectl cp backup.sql postgres-0:/tmp/backup.sql -n bugstracker-production

# Restore
kubectl exec postgres-0 -n bugstracker-production -- \
  psql -U postgres bugstracker < /tmp/backup.sql
```

## Security Best Practices

1. **Secrets Management:**
   - Never commit secrets to git
   - Use Kubernetes secrets or external secret managers (AWS Secrets Manager, HashiCorp Vault)
   - Rotate secrets regularly

2. **Network Policies:**
   ```bash
   kubectl apply -f infrastructure/kubernetes/network-policies.yaml
   ```

3. **RBAC:**
   - Use service accounts with minimal permissions
   - Enable audit logging

4. **Container Security:**
   - Run containers as non-root user
   - Use read-only root filesystem where possible
   - Keep images updated

5. **TLS/SSL:**
   - Use Let's Encrypt for automatic certificate management
   - Enable HTTPS redirect in ingress

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD:

- **CI Pipeline** (`.github/workflows/ci.yml`):
  - Linting (Black, isort, flake8)
  - Type checking (mypy)
  - Unit tests with coverage
  - Security scanning
  - Docker image builds

- **CD Pipeline** (`.github/workflows/cd.yml`):
  - Build and push Docker images
  - Deploy to staging (on main branch)
  - Deploy to production (on version tags)
  - Run migrations
  - Health checks
  - Slack notifications

### Triggering Deployments

```bash
# Deploy to staging (automatic on push to main)
git push origin main

# Deploy to production (create release tag)
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Support and Contact

For deployment issues or questions:
- GitHub Issues: https://github.com/yourusername/bugstracker/issues
- Slack: #bugstracker-ops
- Email: ops@bugstracker.com

---

**Last updated:** 2026-02-15
