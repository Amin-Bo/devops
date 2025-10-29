Ansible playbook for Minikube deployment
======================================

What this does
- Builds the `flask-crud-metrics:latest` image into Minikube (prefers `minikube image build`, falls back to `docker build` + `minikube image load`).
- Applies Kubernetes manifests in `k8s/` (Prometheus, app, Grafana).
- Waits for rollouts to finish and prints service URLs.
- Includes a `clean` tag to delete resources created by the playbook.

Quick usage (Linux / Bash)

```bash
cd ansible
# Syntax check (optional)
ansible-playbook deploy.yml --syntax-check

# Deploy (default)
ansible-playbook deploy.yml -i inventory.ini

# Build only
ansible-playbook deploy.yml -i inventory.ini --tags build

# Apply manifests only
ansible-playbook deploy.yml -i inventory.ini --tags apply

# Delete/clean resources created by the playbook
ansible-playbook deploy.yml -i inventory.ini --tags delete
```

Notes
This playbook runs on `localhost` and assumes `kubectl`, `minikube` and optionally `docker` are available in PATH.
If you prefer to use Ansible Kubernetes modules (`kubernetes.core`), you can replace `kubectl` commands with the `k8s` module and pass a `kubeconfig` path.
