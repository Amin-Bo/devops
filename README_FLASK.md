# Flask CRUD app with Prometheus & Grafana — Minikube guide

This folder contains a small in-memory Flask CRUD application instrumented with Prometheus metrics, plus Kubernetes manifests to run the app, Prometheus and Grafana in Minikube.

This README documents how to:
- build and load the image into Minikube
- deploy the manifests
- access the services (NodePort)
- verify metrics are collected and visualised in Grafana
- common troubleshooting steps

## Prerequisites
- Minikube and kubectl installed and configured
- Docker (optional, only if not using `minikube image build`)
- You are working from the repo root where the `k8s/` folder lives.

## Quick overview of important files
- `k8s/deployment.yaml` — Flask app Deployment (image: `flask-crud-metrics:latest`)
- `k8s/service.yaml` — Service for the Flask app (NodePort targetPort 3000)
- `k8s/flask-app/` — Flask app source, `Dockerfile`, `requirements.txt`
- `k8s/prometheus-*` — Prometheus ConfigMap / Deployment / Service
- `k8s/grafana-*` — Grafana Deployment / Service
- `k8s/grafana-dashboard-flask.json` — ready-to-import Grafana dashboard

---

## 1) Build the Flask image into Minikube

Recommended: build directly into Minikube (no extra push/load required):

```powershell
minikube image build -t flask-crud-metrics:latest .\k8s\flask-app
```

Alternative: build locally and load into Minikube:

```powershell
docker build -t flask-crud-metrics:latest .\k8s\flask-app
minikube image load flask-crud-metrics:latest
```

---

## 2) Deploy manifests
Apply manifests in a safe order so Prometheus exists before the app exposing metrics:

```powershell
# Prometheus (configmap -> deployment -> service)
kubectl apply -f .\k8s\prometheus-configmap.yaml
kubectl apply -f .\k8s\prometheus-deployment.yaml
kubectl apply -f .\k8s\prometheus-service.yaml

# App
kubectl apply -f .\k8s\deployment.yaml
kubectl apply -f .\k8s\service.yaml

# Grafana
kubectl apply -f .\k8s\grafana-deployment.yaml
kubectl apply -f .\k8s\grafana-service.yaml

# Ensure Prometheus reloads the ConfigMap
kubectl rollout restart deployment/prometheus
kubectl rollout status deployment/prometheus
```

---

## 3) Accessing services (NodePort)

The manifests use NodePort by default for external access. Typical ports in this project:
- Grafana NodePort: `32000` → URL: `http://<minikube-ip>:32000`
- Prometheus NodePort: `30090` → URL: `http://<minikube-ip>:30090`

Get the Minikube IP and open the URLs:

```powershell
$ip = minikube ip
Write-Output $ip
# open http://$ip:32000 for Grafana
```

---

## 4) Import Grafana dashboard

1. Open Grafana (`http://<minikube-ip>:32000`) and log in (default `admin`/`admin` if unchanged).
2. Add a Prometheus data source: URL `http://prometheus-service:9090` (Grafana runs in-cluster so use the ClusterIP service name).
3. Import `k8s/grafana-dashboard-flask.json` via Grafana → Create → Import.

---

## 5) Exercise the app and check metrics

Create an item (replace `<MINIKUBE_IP>` and `<NODEPORT>` or use `minikube service`):

```powershell
# get service url
$crudUrl = minikube service crud-service --url
Invoke-RestMethod -Method Post -Uri "$crudUrl/items" -ContentType "application/json" -Body '{"name":"alice"}'

# check metrics exposed by the app
Invoke-RestMethod -Uri "$crudUrl/metrics"
```

Prometheus should be scraping the app (configured to hit `crud-service:80/metrics`). In Prometheus UI check `Status → Targets` for job `crud-app`.

Useful Prometheus queries:
- `up{job="crud-app"}` — whether the app target is up
- `http_requests_total` — total requests counter
- `sum(rate(http_requests_total[1m]))` — overall request rate
- `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))` — p95 latency by route

---

## 6) Restarting and redeploying

Rolling restart every deployment:

```powershell
kubectl rollout restart deployment --all
kubectl rollout status deployment --all
```

Force a redeploy that pulls the image (if you rebuilt an image with the same tag):

```powershell
kubectl set image deployment/crud-app crud-app=flask-crud-metrics:latest --record
kubectl rollout status deployment/crud-app
```

---

## 7) Clean deletion

To remove all resources created from this folder:

```powershell
kubectl delete -f .\k8s --recursive --ignore-not-found=true
```

---

## 8) Troubleshooting
- **Pod not starting**: `kubectl logs <pod-name>` and `kubectl describe pod <pod-name>`
- **Prometheus target DOWN**: check Prometheus logs: `kubectl logs -l app=prometheus --tail=200` and inspect `prometheus-config` ConfigMap: `kubectl get configmap prometheus-config -o yaml`
- **Grafana can't talk to Prometheus**: verify Grafana data source uses `http://prometheus-service:9090` (in-cluster address) and check Grafana logs: `kubectl logs -l app=grafana --tail=200`
- **NodePort not reachable**: ensure the NodePort values (30090, 32000) are available and Minikube IP is reachable from your host

---

## 9) Notes and recommendations
- The Flask app stores items in memory — pod restarts clear data. For production, add persistent storage or an external DB.
- For production-like setups, consider using Helm charts for Prometheus/Grafana and enabling TLS on an Ingress with cert-manager.

---

If you'd like, I can add a small PowerShell script `k8s/deploy.ps1` that automates the build + apply sequence and `k8s/clean.ps1` to delete resources.
Flask CRUD app with Prometheus metrics — Minikube steps

Overview
- Simple in-memory Flask CRUD app that exposes Prometheus metrics at /metrics.

Build the image into Minikube
Option A (recommended): use minikube image build
```powershell
minikube image build -t flask-crud-metrics:latest .\k8s\flask-app
```

Option B: build locally and load into minikube
```powershell
docker build -t flask-crud-metrics:latest .\k8s\flask-app
minikube image load flask-crud-metrics:latest
```

Apply Kubernetes manifests
```powershell
kubectl apply -f .\k8s\prometheus-configmap.yaml
kubectl apply -f .\k8s\prometheus-deployment.yaml
kubectl apply -f .\k8s\prometheus-service.yaml
kubectl apply -f .\k8s\blackbox-deployment.yaml
kubectl apply -f .\k8s\blackbox-service.yaml
kubectl apply -f .\k8s\deployment.yaml
kubectl apply -f .\k8s\service.yaml
kubectl apply -f .\k8s\grafana-deployment.yaml
kubectl apply -f .\k8s\grafana-service.yaml

# restart prometheus so it reads the updated ConfigMap
kubectl rollout restart deployment/prometheus
```

Verify
- Prometheus: `minikube service prometheus-service --url` → open and check Status → Targets (job `crud-app`) and query `http_requests_total`.
- Grafana: `minikube service grafana-service --url` → import dashboard JSON if provided.
