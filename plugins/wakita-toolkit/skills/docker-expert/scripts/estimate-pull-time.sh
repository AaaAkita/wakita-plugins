#!/bin/bash
# Docker 镜像拉取时间预估脚本
# 根据镜像大小和当前网络速度，预估拉取时间并推荐超时设置
#
# 使用方法：bash estimate-pull-time.sh [镜像名:标签]
# 示例：bash estimate-pull-time.sh nginx:latest
#       bash estimate-pull-time.sh python:3.11-slim

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认值
DEFAULT_IMAGE="nginx:latest"
DEFAULT_TIMEOUT_MULTIPLIER=2.0  # 超时倍数（预估时间 × 倍数）
MIN_TIMEOUT=60                   # 最小超时时间（秒）
MAX_TIMEOUT=3600                 # 最大超时时间（秒）

# 获取输入参数
IMAGE="${1:-$DEFAULT_IMAGE}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Docker 镜像拉取时间预估工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "目标镜像: ${YELLOW}${IMAGE}${NC}"
echo ""

# 步骤 1：测试当前网络速度
echo -e "${YELLOW}[1/3] 测试当前网络速度...${NC}"

# 测试到 Docker Hub 的连接速度
echo -ne "  测试 Docker Hub 连接速度... "
START_TIME=$(date +%s%N)

# 使用小文件测试速度
TEST_URL="https://registry-1.docker.io/v2/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$TEST_URL" 2>/dev/null || echo "000")

END_TIME=$(date +%s%N)
LATENCY=$(( (END_TIME - START_TIME) / 1000000 ))

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
    echo -e "${GREEN}✓ ${LATENCY}ms${NC}"
else
    echo -e "${RED}✗ 连接失败 (HTTP ${HTTP_CODE})${NC}"
    echo -e "${YELLOW}  将使用默认速度估算${NC}"
    LATENCY=1000
fi

# 测试下载速度（使用小文件）
echo -ne "  测试下载速度... "
SPEED_TEST_URL="https://speed.cloudflare.com/__down?bytes=1048576"  # 1MB
SPEED_START=$(date +%s%N)
curl -s -o /dev/null --connect-timeout 5 --max-time 10 "$SPEED_TEST_URL" 2>/dev/null
SPEED_END=$(date +%s%N)
SPEED_TIME=$(( (SPEED_END - SPEED_START) / 1000000 ))

if [ "$SPEED_TIME" -gt 0 ]; then
    # 估算速度（MB/s）
    SPEED_MBPS=$(echo "scale=2; 1000 / $SPEED_TIME" | bc 2>/dev/null || echo "1.0")
    echo -e "${GREEN}✓ ${SPEED_MBPS} MB/s${NC}"
else
    SPEED_MBPS="1.0"
    echo -e "${YELLOW}? 无法测试，使用默认值 ${SPEED_MBPS} MB/s${NC}"
fi

echo ""

# 步骤 2：获取镜像大小信息
echo -e "${YELLOW}[2/3] 获取镜像大小信息...${NC}"

# 尝试获取镜像 manifest
echo -ne "  查询镜像信息... "

# 获取 token
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${IMAGE%%:*}:pull" 2>/dev/null | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    # 获取 manifest
    MANIFEST=$(curl -s -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json" \
        "https://registry-1.docker.io/v2/${IMAGE%%:*}/manifests/${IMAGE##*:}" 2>/dev/null)
    
    # 尝试解析大小
    if echo "$MANIFEST" | grep -q "totalSize"; then
        # manifest v2 格式
        TOTAL_SIZE=$(echo "$MANIFEST" | grep -o '"totalSize":[0-9]*' | head -1 | cut -d':' -f2)
        if [ -n "$TOTAL_SIZE" ]; then
            SIZE_MB=$(echo "scale=2; $TOTAL_SIZE / 1048576" | bc 2>/dev/null || echo "未知")
            echo -e "${GREEN}✓ ${SIZE_MB} MB${NC}"
        else
            SIZE_MB="100"  # 默认估算
            echo -e "${YELLOW}? 无法解析，使用默认估算 ${SIZE_MB} MB${NC}"
        fi
    elif echo "$MANIFEST" | grep -q "configSize"; then
        # manifest list 格式
        TOTAL_SIZE=$(echo "$MANIFEST" | grep -o '"configSize":[0-9]*' | head -1 | cut -d':' -f2)
        if [ -n "$TOTAL_SIZE" ]; then
            SIZE_MB=$(echo "scale=2; $TOTAL_SIZE / 1048576" | bc 2>/dev/null || echo "未知")
            echo -e "${GREEN}✓ ${SIZE_MB} MB${NC}"
        else
            SIZE_MB="100"
            echo -e "${YELLOW}? 无法解析，使用默认估算 ${SIZE_MB} MB${NC}"
        fi
    else
        SIZE_MB="100"
        echo -e "${YELLOW}? 无法获取，使用默认估算 ${SIZE_MB} MB${NC}"
    fi
else
    SIZE_MB="100"
    echo -e "${YELLOW}? 无法获取 token，使用默认估算 ${SIZE_MB} MB${NC}"
fi

echo ""

# 步骤 3：预估拉取时间
echo -e "${YELLOW}[3/3] 预估拉取时间...${NC}"

# 计算预估时间（秒）
# 公式：时间 = 大小(MB) / 速度(MB/s) + 延迟补偿
DELAY_COMPENSATION=$(echo "scale=0; $LATENCY / 1000" | bc 2>/dev/null || echo "1")
PULL_TIME=$(echo "scale=0; ($SIZE_MB / $SPEED_MBPS) + $DELAY_COMPENSATION" | bc 2>/dev/null || echo "60")

# 确保是整数
PULL_TIME=${PULL_TIME%.*}
if [ -z "$PULL_TIME" ] || [ "$PULL_TIME" -lt 1 ]; then
    PULL_TIME=60
fi

# 计算推荐超时时间
RECOMMENDED_TIMEOUT=$(echo "scale=0; $PULL_TIME * $DEFAULT_TIMEOUT_MULTIPLIER" | bc 2>/dev/null || echo "120")
RECOMMENDED_TIMEOUT=${RECOMMENDED_TIMEOUT%.*}

# 应用最小/最大限制
if [ "$RECOMMENDED_TIMEOUT" -lt "$MIN_TIMEOUT" ]; then
    RECOMMENDED_TIMEOUT=$MIN_TIMEOUT
fi
if [ "$RECOMMENDED_TIMEOUT" -gt "$MAX_TIMEOUT" ]; then
    RECOMMENDED_TIMEOUT=$MAX_TIMEOUT
fi

# 输出结果
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   预估结果${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  镜像大小:         ${GREEN}${SIZE_MB} MB${NC}"
echo -e "  当前网速:         ${GREEN}${SPEED_MBPS} MB/s${NC}"
echo -e "  网络延迟:         ${GREEN}${LATENCY} ms${NC}"
echo -e "  预估拉取时间:     ${GREEN}${PULL_TIME} 秒${NC}"
echo -e "  推荐超时时间:     ${GREEN}${RECOMMENDED_TIMEOUT} 秒${NC}"
echo ""

# 输出使用建议
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   使用建议${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$PULL_TIME" -lt 30 ]; then
    echo -e "${GREEN}✓ 小型镜像，拉取很快${NC}"
    echo "  - 适合开发环境频繁拉取"
    echo "  - 超时设置 60-120 秒足够"
elif [ "$PULL_TIME" -lt 120 ]; then
    echo -e "${YELLOW}⚠ 中型镜像，需要一定时间${NC}"
    echo "  - 建议配置国内镜像源加速"
    echo "  - 超时设置 180-300 秒"
elif [ "$PULL_TIME" -lt 300 ]; then
    echo -e "${YELLOW}⚠ 大型镜像，需要较长时间${NC}"
    echo "  - 强烈建议配置国内镜像源"
    echo "  - 考虑使用多阶段构建减小镜像"
    echo "  - 超时设置 600-900 秒"
else
    echo -e "${RED}✗ 超大型镜像，拉取时间很长${NC}"
    echo "  - 必须配置国内镜像源"
    echo "  - 考虑使用 Docker Hub 代理服务"
    echo "  - 考虑手动导入/导出镜像"
    echo "  - 超时设置 1800-3600 秒"
fi

echo ""

# 输出 Docker Compose 超时配置示例
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Docker Compose 超时配置示例${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}在 docker-compose.yml 中配置：${NC}"
echo ""
echo '```yaml'
echo 'services:'
echo '  app:'
echo '    image: '"${IMAGE}"
echo '    # 方式 1：使用 deploy 超时配置'
echo '    deploy:'
echo '      restart_policy:'
echo '        delay: 5s'
echo '        max_attempts: 3'
echo '        window: 120s'
echo ''
echo '    # 方式 2：使用 healthcheck 配合超时'
echo '    healthcheck:'
echo '      test: ["CMD", "curl", "-f", "http://localhost/"]'
echo '      interval: 30s'
echo '      timeout: '"${RECOMMENDED_TIMEOUT}"'s'
echo '      retries: 3'
echo '      start_period: 60s'
echo '```'
echo ""

echo -e "${YELLOW}设置 Docker 客户端超时（环境变量）：${NC}"
echo ""
echo "  # Linux/macOS"
echo "  export DOCKER_CLIENT_TIMEOUT=${RECOMMENDED_TIMEOUT}"
echo "  export COMPOSE_HTTP_TIMEOUT=${RECOMMENDED_TIMEOUT}"
echo ""
echo "  # Windows (PowerShell)"
echo "  \$env:DOCKER_CLIENT_TIMEOUT=\"${RECOMMENDED_TIMEOUT}\""
echo "  \$env:COMPOSE_HTTP_TIMEOUT=\"${RECOMMENDED_TIMEOUT}\""
echo ""

echo -e "${BLUE}========================================${NC}"