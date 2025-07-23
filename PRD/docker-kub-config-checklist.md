# Docker/Kubernetes Configuration Checklist

## Docker Configuration

### Multi-Stage Dockerfile
- [ ] Create optimized `Dockerfile`:
```dockerfile
# Build stage
FROM node:18-alpine AS builder

# Install build dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install all dependencies
RUN npm ci

# Copy source code
COPY src ./src

# Build application
RUN npm run build

# Production dependencies stage
FROM node:18-alpine AS deps

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Runtime stage
FROM node:18-alpine

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

WORKDIR /app

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs package*.json ./

# Create necessary directories
RUN mkdir -p /app/logs && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD node dist/healthcheck.js || exit 1

# Use dumb-init to handle signals
ENTRYPOINT ["dumb-init", "--"]

# Start application
CMD ["node", "dist/index.js"]
```

### Docker Compose Development
- [ ] Create `docker-compose.dev.yml`:
```yaml
version: '3.8'

services:
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
      - "9229:9229" # Debug port
    environment:
      - NODE_ENV=development
      - LOG_LEVEL=debug
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
      - ~/.skyfi:/home/node/.skyfi:ro
    depends_on:
      - redis
      - postgres
    command: npm run dev

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: skyfi_mcp
      POSTGRES_USER: skyfi
      POSTGRES_PASSWORD: development
    volumes:
      - postgres-data:/var/lib/postgresql/data

  adminer:
    image: adminer
    ports:
      - "8080:8080"
    depends_on:
      - postgres

volumes:
  redis-data:
  postgres-data:
```

### Docker Compose Production
- [ ] Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  mcp-server:
    image: gcr.io/skyfi-project/mcp-server:${VERSION:-latest}
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=info
    env_file:
      - .env.production
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - mcp-server
```

### Development Dockerfile
- [ ] Create `Dockerfile.dev`:
```dockerfile
FROM node:18-alpine

RUN apk add --no-cache python3 make g++

WORKDIR /app

# Install nodemon globally
RUN npm install -g nodemon ts-node

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Expose debug port
EXPOSE 9229

CMD ["npm", "run", "dev:debug"]
```

## Kubernetes Configuration

### Namespace and RBAC
- [ ] Create `k8s/00-namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: skyfi-mcp
  labels:
    name: skyfi-mcp
    environment: production
```

- [ ] Create `k8s/01-rbac.yaml`:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-server
  namespace: skyfi-mcp
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mcp-server-role
  namespace: skyfi-mcp
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mcp-server-rolebinding
  namespace: skyfi-mcp
subjects:
- kind: ServiceAccount
  name: mcp-server
  namespace: skyfi-mcp
roleRef:
  kind: Role
  name: mcp-server-role
  apiGroup: rbac.authorization.k8s.io
```

### ConfigMaps and Secrets
- [ ] Create `k8s/02-configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-server-config
  namespace: skyfi-mcp
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  PORT: "3000"
  SKYFI_API_URL: "https://app.skyfi.com/platform-api"
  REDIS_URL: "redis://redis-service:6379"
  ENABLE_METRICS: "true"
  METRICS_PORT: "9090"
  
  # Rate limiting
  RATE_LIMIT_WINDOW_MS: "60000"
  RATE_LIMIT_MAX_FREE: "100"
  RATE_LIMIT_MAX_PRO: "1000"
  
  # Caching
  CACHE_TTL_SECONDS: "300"
  CACHE_MAX_KEYS: "10000"
```

- [ ] Create secret template `k8s/02-secret-template.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-server-secrets
  namespace: skyfi-mcp
type: Opaque
stringData:
  SKYFI_API_KEY: "sk-production-key"
  OPENWEATHER_API_KEY: "weather-api-key"
  DATABASE_URL: "postgresql://user:pass@postgres:5432/skyfi"
  JWT_SECRET: "your-jwt-secret"
  SENTRY_DSN: "https://key@sentry.io/project"
```

### StatefulSet for Redis
- [ ] Create `k8s/03-redis.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: skyfi-mcp
spec:
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
  selector:
    app: redis
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: skyfi-mcp
spec:
  serviceName: redis-service
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
          - redis-server
          - --appendonly
          - "yes"
          - --appendfsync
          - "everysec"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### Main Application Deployment
- [ ] Create `k8s/04-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: skyfi-mcp
  labels:
    app: mcp-server
    version: v1
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: mcp-server
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
      containers:
      - name: mcp-server
        image: gcr.io/skyfi-project/mcp-server:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 3000
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP
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
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - mcp-server
              topologyKey: kubernetes.io/hostname
```

### Service and Ingress
- [ ] Create `k8s/05-service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
  namespace: skyfi-mcp
  labels:
    app: mcp-server
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: metrics
    protocol: TCP
  selector:
    app: mcp-server
```

- [ ] Create `k8s/06-ingress.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-server-ingress
  namespace: skyfi-mcp
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
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

### Autoscaling Configuration
- [ ] Create `k8s/07-hpa.yaml`:
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
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
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

### Monitoring and Observability
- [ ] Create `k8s/08-monitoring.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-metrics
  namespace: skyfi-mcp
  labels:
    app: mcp-server
    service: metrics
spec:
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
  selector:
    app: mcp-server
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-server-monitor
  namespace: skyfi-mcp
spec:
  selector:
    matchLabels:
      app: mcp-server
      service: metrics
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Network Policies
- [ ] Create `k8s/09-network-policy.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-network-policy
  namespace: skyfi-mcp
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 3000
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443 # HTTPS for external APIs
    - protocol: TCP
      port: 53  # DNS
    - protocol: UDP
      port: 53  # DNS
```

### Pod Disruption Budget
- [ ] Create `k8s/10-pdb.yaml`:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: mcp-server-pdb
  namespace: skyfi-mcp
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: mcp-server
```

## Deployment Scripts

### Kubernetes Deployment Script
- [ ] Create `scripts/deploy-k8s.sh`:
```bash
#!/bin/bash
set -e

NAMESPACE="skyfi-mcp"
VERSION=${1:-latest}

echo "Deploying SkyFi MCP Server version: $VERSION"

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply configurations in order
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-rbac.yaml
kubectl apply -f k8s/02-configmap.yaml

# Check if secrets exist, if not create from template
if ! kubectl get secret mcp-server-secrets -n $NAMESPACE &> /dev/null; then
    echo "Creating secrets from template..."
    kubectl apply -f k8s/02-secret-template.yaml
fi

# Deploy Redis
kubectl apply -f k8s/03-redis.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=120s

# Update deployment image
kubectl set image deployment/mcp-server mcp-server=gcr.io/skyfi-project/mcp-server:$VERSION -n $NAMESPACE --record || true

# Apply remaining configurations
kubectl apply -f k8s/04-deployment.yaml
kubectl apply -f k8s/05-service.yaml
kubectl apply -f k8s/06-ingress.yaml
kubectl apply -f k8s/07-hpa.yaml
kubectl apply -f k8s/08-monitoring.yaml
kubectl apply -f k8s/09-network-policy.yaml
kubectl apply -f k8s/10-pdb.yaml

# Wait for rollout to complete
kubectl rollout status deployment/mcp-server -n $NAMESPACE

echo "Deployment complete!"
kubectl get pods -n $NAMESPACE
```

### Docker Build Script
- [ ] Create `scripts/build-docker.sh`:
```bash
#!/bin/bash
set -e

VERSION=${1:-latest}
REGISTRY="gcr.io/skyfi-project"
IMAGE_NAME="mcp-server"

echo "Building Docker image version: $VERSION"

# Build image
docker build -t $IMAGE_NAME:$VERSION .

# Tag for registry
docker tag $IMAGE_NAME:$VERSION $REGISTRY/$IMAGE_NAME:$VERSION
docker tag $IMAGE_NAME:$VERSION $REGISTRY/$IMAGE_NAME:latest

# Push to registry
echo "Pushing to registry..."
docker push $REGISTRY/$IMAGE_NAME:$VERSION
docker push $REGISTRY/$IMAGE_NAME:latest

echo "Build and push complete!"
```

## Helm Chart (Optional)
- [ ] Create Helm chart structure
- [ ] Define values.yaml with configurable options
- [ ] Create templates for all resources
- [ ] Add chart dependencies
- [ ] Create chart README
- [ ] Package and publish chart