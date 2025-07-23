# Deployment Checklist

## Pre-Deployment Verification
- [ ] All tests passing (`npm test`)
- [ ] No linting errors (`npm run lint`)
- [ ] Build successful (`npm run build`)
- [ ] Security audit passed (`npm audit`)
- [ ] Environment variables documented
- [ ] API keys and secrets secured

## Local Deployment

### Docker Setup
- [ ] Create `Dockerfile`:
  ```dockerfile
  FROM node:18-alpine AS builder
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci --only=production
  
  FROM node:18-alpine
  WORKDIR /app
  COPY --from=builder /app/node_modules ./node_modules
  COPY dist ./dist
  COPY package*.json ./
  EXPOSE 3000
  CMD ["node", "dist/index.js"]
  ```
- [ ] Create `.dockerignore`:
  ```
  node_modules
  src
  tests
  .env
  .git
  coverage
  *.log
  ```
- [ ] Build Docker image:
  ```bash
  docker build -t skyfi-mcp-server:latest .
  ```
- [ ] Test Docker container:
  ```bash
  docker run -p 3000:3000 --env-file .env skyfi-mcp-server:latest
  ```

### Docker Compose Setup
- [ ] Create `docker-compose.yml`:
  ```yaml
  version: '3.8'
  services:
    mcp-server:
      build: .
      ports:
        - "3000:3000"
      environment:
        - NODE_ENV=production
        - REDIS_URL=redis://redis:6379
      volumes:
        - ~/.skyfi:/root/.skyfi:ro
      depends_on:
        - redis
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
  ```
- [ ] Create `docker-compose.dev.yml` for development
- [ ] Test compose stack: `docker-compose up`
- [ ] Verify health check: `curl http://localhost:3000/health`

### Local SSL Setup
- [ ] Generate self-signed certificates
- [ ] Configure HTTPS in Express
- [ ] Update local hosts file if needed
- [ ] Test HTTPS endpoint

## Cloud Deployment (AWS/GCP)

### Container Registry
- [ ] Tag image for registry:
  ```bash
  docker tag skyfi-mcp-server:latest gcr.io/skyfi-project/mcp-server:v1.0.0
  ```
- [ ] Push to registry:
  ```bash
  docker push gcr.io/skyfi-project/mcp-server:v1.0.0
  ```
- [ ] Verify image in registry console
- [ ] Set up vulnerability scanning

### Kubernetes Configuration
- [ ] Create namespace:
  ```yaml
  apiVersion: v1
  kind: Namespace
  metadata:
    name: skyfi-mcp
  ```
- [ ] Create ConfigMap for non-sensitive config:
  ```yaml
  apiVersion: v1
  kind: ConfigMap
  metadata:
    name: mcp-server-config
    namespace: skyfi-mcp
  data:
    NODE_ENV: "production"
    SKYFI_API_URL: "https://app.skyfi.com/platform-api"
  ```
- [ ] Create Secret for sensitive data:
  ```bash
  kubectl create secret generic mcp-server-secrets \
    --from-literal=SKYFI_API_KEY=sk-production-key \
    --from-literal=OPENWEATHER_API_KEY=weather-key \
    -n skyfi-mcp
  ```

### Deployment Configuration
- [ ] Create `k8s/deployment.yaml`:
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: mcp-server
    namespace: skyfi-mcp
  spec:
    replicas: 3
    selector:
      matchLabels:
        app: mcp-server
    template:
      metadata:
        labels:
          app: mcp-server
      spec:
        containers:
        - name: mcp-server
          image: gcr.io/skyfi-project/mcp-server:v1.0.0
          ports:
          - containerPort: 3000
          envFrom:
          - configMapRef:
              name: mcp-server-config
          - secretRef:
              name: mcp-server-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
  ```

### Service Configuration
- [ ] Create `k8s/service.yaml`:
  ```yaml
  apiVersion: v1
  kind: Service
  metadata:
    name: mcp-server-service
    namespace: skyfi-mcp
  spec:
    selector:
      app: mcp-server
    ports:
    - port: 80
      targetPort: 3000
    type: LoadBalancer
  ```

### Ingress/Load Balancer
- [ ] Create `k8s/ingress.yaml`:
  ```yaml
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: mcp-server-ingress
    namespace: skyfi-mcp
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
      kubernetes.io/ingress.class: "nginx"
  spec:
    tls:
    - hosts:
      - mcp.skyfi.com
      secretName: mcp-server-tls
    rules:
    - host: mcp.skyfi.com
      http:
        paths:
        - path: /
          pathType: Prefix
          backend:
            service:
              name: mcp-server-service
              port:
                number: 80
  ```
- [ ] Configure SSL certificate with cert-manager
- [ ] Set up domain DNS records
- [ ] Test HTTPS endpoint

### Auto-scaling
- [ ] Create HorizontalPodAutoscaler:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: mcp-server-hpa
    namespace: skyfi-mcp
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: mcp-server
    minReplicas: 3
    maxReplicas: 20
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  ```

### Redis Deployment
- [ ] Deploy Redis cluster or use managed service
- [ ] Configure connection pooling
- [ ] Set up Redis Sentinel for HA
- [ ] Configure persistence and backups

## Monitoring Setup

### Application Monitoring
- [ ] Install Prometheus operator
- [ ] Configure ServiceMonitor:
  ```yaml
  apiVersion: monitoring.coreos.com/v1
  kind: ServiceMonitor
  metadata:
    name: mcp-server-monitor
    namespace: skyfi-mcp
  spec:
    selector:
      matchLabels:
        app: mcp-server
    endpoints:
    - port: metrics
      interval: 30s
  ```
- [ ] Set up Grafana dashboards
- [ ] Configure alerts for:
  - [ ] High error rate (>5%)
  - [ ] High latency (>500ms p95)
  - [ ] Pod restarts
  - [ ] Memory/CPU usage

### Logging
- [ ] Configure centralized logging (ELK/EFK stack)
- [ ] Set up log aggregation
- [ ] Configure log retention policies
- [ ] Create log-based alerts

### Error Tracking
- [ ] Configure Sentry integration
- [ ] Set up error notifications
- [ ] Configure source maps for debugging
- [ ] Test error reporting

## Security Hardening

### Network Security
- [ ] Configure NetworkPolicies
- [ ] Set up WAF rules
- [ ] Enable DDoS protection
- [ ] Configure rate limiting at ingress

### Container Security
- [ ] Run security scan on images
- [ ] Use non-root user in container
- [ ] Enable read-only root filesystem
- [ ] Configure SecurityContext:
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
      - ALL
  ```

### Secrets Management
- [ ] Use Kubernetes Secrets or external secret manager
- [ ] Enable encryption at rest
- [ ] Rotate secrets regularly
- [ ] Audit secret access

## Deployment Verification

### Smoke Tests
- [ ] Health check endpoint responding
- [ ] Authentication working
- [ ] Core tools accessible
- [ ] Rate limiting active
- [ ] SSL certificate valid

### Load Testing
- [ ] Run k6 load tests:
  ```javascript
  import http from 'k6/http';
  import { check } from 'k6';
  
  export let options = {
    stages: [
      { duration: '2m', target: 100 },
      { duration: '5m', target: 100 },
      { duration: '2m', target: 0 },
    ],
  };
  
  export default function() {
    let response = http.get('https://mcp.skyfi.com/health');
    check(response, { 'status is 200': (r) => r.status === 200 });
  }
  ```
- [ ] Verify auto-scaling triggers
- [ ] Check resource utilization
- [ ] Monitor error rates

### Integration Tests
- [ ] Test all API endpoints
- [ ] Verify external service connectivity
- [ ] Test failover scenarios
- [ ] Verify backup procedures

## Post-Deployment

### Documentation
- [ ] Update deployment guide
- [ ] Document rollback procedures
- [ ] Create runbook for common issues
- [ ] Update API documentation with production URLs

### Monitoring Setup
- [ ] Configure dashboards for:
  - [ ] Request rate
  - [ ] Error rate
  - [ ] Response time
  - [ ] Resource usage
- [ ] Set up on-call rotation
- [ ] Configure PagerDuty integration
- [ ] Test alert notifications

### Backup and Recovery
- [ ] Configure automated backups
- [ ] Test restore procedures
- [ ] Document disaster recovery plan
- [ ] Set up cross-region replication 
