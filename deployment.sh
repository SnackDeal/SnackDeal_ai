#!/bin/bash
set -e

IMAGE="ghcr.io/YOUR_GITHUB_ORG/snackdeal-ai:latest"  # TODO: 실제 GitHub 조직명으로 교체
CONTAINER_NAME="snackdeal-ai"
PORT=8000

echo "=== [1] 최신 이미지 풀 ==="
docker pull "$IMAGE"

echo "=== [2] 기존 컨테이너 중지 & 제거 ==="
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  docker stop "$CONTAINER_NAME"
  docker rm "$CONTAINER_NAME"
fi

echo "=== [3] 새 컨테이너 실행 ==="
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "$PORT:8000" \
  --env-file /home/ubuntu/snackdeal-ai/.env \
  "$IMAGE"

echo "=== [4] 오래된 이미지 정리 ==="
docker image prune -f

echo "=== 배포 완료 ==="
