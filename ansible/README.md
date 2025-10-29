Ansible playbook for Minikube deployment
======================================

What this does
- Builds the `flask-crud-metrics:latest` image into Minikube (prefers `minikube image build`, falls back to `docker build` + `minikube image load`).
- Applies Kubernetes manifests in `k8s/` (Prometheus, app, Grafana).
- Waits for rollouts to finish and prints service URLs.
- Includes a `clean` tag to delete resources created by the playbook.

Quick usage (PowerShell)

```powershell
cd k8s\ansible
# Syntax check (optional)
ansible-playbook deploy.yml --syntax-check

# Deploy (default)
ansible-playbook deploy.yml -i inventory.ini

# Run only the build+deploy tasks (tag 'deploy' is default)
ansible-playbook deploy.yml -i inventory.ini --tags deploy

# Clean the cluster resources created by the playbook
ansible-playbook deploy.yml -i inventory.ini --tags clean
```

Notes
- This playbook runs on `localhost` and assumes `kubectl`, `minikube` and optionally `docker` are available in PATH.
- If you prefer to use Ansible Kubernetes modules (kubernetes.core), you can replace `kubectl` commands with `k8s` module tasks and pass a `kubeconfig` path.
