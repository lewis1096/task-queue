# taskqueue

Async task queue library backed by Postgres. Provides durable job queuing with at-least-once delivery, automatic retries with exponential backoff, dead-letter handling, and lease-based failure detection. Designed to run in Kubernetes with zero infrastructure beyond the database.

## Architecture

Everything runs locally inside a minikube cluster on Docker Desktop. You interact via `kubectl` from your terminal.

![Local development architecture](docs/architecture.svg)

- **Postgres** — single pod, stores all job state
- **Producer** — enqueues fake jobs in a loop
- **Workers (x3)** — compete for jobs via `SELECT ... FOR UPDATE SKIP LOCKED`
- **Lease reaper** — CronJob that reclaims stuck jobs every 30s
- **TTL cleanup** — CronJob that deletes old completed/dead-lettered jobs daily

In production, the same architecture runs on a real Kubernetes cluster in the cloud. Your Mac pushes images to a container registry and applies manifests via `kubectl`.

![Cloud architecture](docs/cloud-architecture.svg)

## Prerequisites

- Python 3.11+
- Postgres 16+
- Docker Desktop
- [minikube](https://minikube.sigs.k8s.io/docs/start/) (`brew install minikube`)
- kubectl (`brew install kubectl`)

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd task_queue

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package and dev dependencies
pip install -e ".[dev]"
```

## Local Kubernetes (minikube)

### Start the cluster

```bash
minikube start --driver=docker --memory=4096 --cpus=2
```

### Deploy Postgres

```bash
kubectl apply -f k8s/
```

This creates:
- **Secret** — database credentials and `DATABASE_URL`
- **PersistentVolumeClaim** — 1GB disk so Postgres data survives pod restarts
- **Deployment** — runs `postgres:16` with the credentials injected
- **Service** — stable DNS name (`postgres:5432`) so other pods can connect

### Verify Postgres is running

```bash
# Watch until you see 1/1 Running, then Ctrl+C
kubectl get pods -l app=postgres -w

# Test the connection from inside the cluster
kubectl run pg-test --rm -it --restart=Never \
  --image=postgres:16 \
  --env="PGPASSWORD=taskqueue-dev-password" \
  -- psql -h postgres -U taskqueue -d taskqueue -c "SELECT 1;"
```

You should see a result of `1`. Press `q` to exit the pager, and the test pod cleans itself up.

### Stopping and restarting

- `minikube stop` — pauses everything, data is preserved
- `minikube start` — brings it back, Kubernetes restarts your pods automatically (no need to re-apply manifests)
- `minikube delete` — destroys the cluster and all data

## Run tests

```bash
pytest
```

## Project structure

```
src/taskqueue/       # Library source code
  __init__.py
  models.py          # Job dataclass
  db.py              # Database connection
tests/               # Test suite
k8s/                 # Kubernetes manifests
  postgres-secret.yaml
  postgres-pvc.yaml
  postgres-deployment.yaml
  postgres-service.yaml
Dockerfile           # Single image, multiple roles via ROLE env var
entrypoint.sh        # Dispatches to producer/worker/reaper/cleanup
pyproject.toml       # Package metadata and dependencies
```

## Docker

```bash
docker build -t taskqueue .

# Run as different roles
docker run -e ROLE=worker -e DATABASE_URL=postgres://... taskqueue
docker run -e ROLE=producer -e DATABASE_URL=postgres://... taskqueue
```
