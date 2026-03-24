# Node.js Express + React Docker Demo

This folder contains two services:

- Backend: Node.js + Express API
- Frontend: React (Vite) served by nginx

## Run locally with Docker Compose

From this folder:

```bash
docker compose up --build -d
```

Test:

- Frontend: http://localhost:8080
- Backend health: http://localhost:3000/api/health

Stop:

```bash
docker compose down
```

## Build and push to Docker Hub

Login:

```bash
docker login
```

Set your Docker Hub username:

```bash
export DOCKERHUB_USER=<your_username>
```

Build images:

```bash
docker build -t $DOCKERHUB_USER/lab-agent-backend:latest ./Backend
docker build -t $DOCKERHUB_USER/lab-agent-frontend:latest ./Frontend
```

Push images:

```bash
docker push $DOCKERHUB_USER/lab-agent-backend:latest
docker push $DOCKERHUB_USER/lab-agent-frontend:latest
```