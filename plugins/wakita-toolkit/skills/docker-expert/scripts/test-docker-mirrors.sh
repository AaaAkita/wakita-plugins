#!/bin/bash
# Docker 镜像源测试脚本
# 测试各镜像源的可用性和传输速度，输出推荐配置
#
# 使用方法：bash test-docker-mirrors.sh
# 输出：可用镜像源列表（按速度排序）+ 推荐配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试用小镜像（约 2MB）
TEST_IMAGE="hello-world"
TEST_CONTENT_TYPE="application/vnd.docker.distribution.manifest.v2+json"

# 镜像源列表
declare -A MIRRORS=(
    # 官方源
    ["Docker Hub (官方)"]="registry-1.docker.io"
    # 国内镜像源
    ["阿里云"]="registry.cn-hangzhou.aliyuncs.com"
    ["腾讯云"]="mirror.ccs.tencentyun.com"
    ["网易"]="hub-mirror.c.163.com"
    ["中科大"]="docker.mirrors.ustc.edu.cn"
    ["华为云"]="huaweicloud.com"
    ["DaoCloud"]="docker.m.daocloud.io"
    ["百度云"]="mirror.baidubcs.com"
    ["七牛云"]="registry.qiniu.com"
    ["Azure"]="dockerhub.azurecr.cn"
)

# 结果存储
declare -A RESULTS=()
declare -A SPEEDS=()

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Docker 镜像源测试工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 测试单个镜像源
test_mirror() {
    local name="$1"
    local host="$2"
    local start_time end_time elapsed time_ms speed
    
    echo -ne "  测试 ${name}... "
    
    # 测试连通性（超时 5 秒）
    if ! curl -s --connect-timeout 5 --max-time 10 "https://${host}/v2/" > /dev/null 2>&1; then
        echo -e "${RED}✗ 不可达${NC}"
        return 1
    fi
    
    # 测试拉取速度（通过 HEAD 请求模拟）
    start_time=$(date +%s%N)
    
    # 获取 token（如果需要）
    local token_url="https://auth.docker.io/token?service=registry.docker.io&scope=repository:${TEST_IMAGE}:pull"
    if [ "$host" = "registry-1.docker.io" ]; then
        curl -s --connect-timeout 5 --max-time 10 "$token_url" > /dev/null 2>&1
    fi
    
    # 测试响应时间
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "https://${host}/v2/")
    
    end_time=$(date +%s%N)
    elapsed=$(( (end_time - start_time) / 1000000 )) # 毫秒
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "401" ]; then
        # 计算速度分数（响应时间越短越好）
        if [ "$elapsed" -lt 500 ]; then
            speed="极快"
            SPEEDS["$name"]=1
        elif [ "$elapsed" -lt 1000 ]; then
            speed="快"
            SPEEDS["$name"]=2
        elif [ "$elapsed" -lt 2000 ]; then
            speed="中等"
            SPEEDS["$name"]=3
        else
            speed="慢"
            SPEEDS["$name"]=4
        fi
        
        RESULTS["$name"]="${host}|${elapsed}ms|${speed}"
        echo -e "${GREEN}✓ ${speed} (${elapsed}ms)${NC}"
        return 0
    else
        echo -e "${YELLOW}? 状态码: ${http_code} (${elapsed}ms)${NC}"
        RESULTS["$name"]="${host}|${elapsed}ms|未知"
        SPEEDS["$name"]=5
        return 1
    fi
}

# 测试所有镜像源
echo -e "${YELLOW}正在测试镜像源连通性和响应速度...${NC}"
echo ""

for name in "${!MIRRORS[@]}"; do
    host="${MIRRORS[$name]}"
    test_mirror "$name" "$host" || true
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   测试结果${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 按速度排序输出
echo -e "${GREEN}可用镜像源（按响应速度排序）：${NC}"
echo ""

# 创建临时文件排序
tmp_file=$(mktemp)
for name in "${!RESULTS[@]}"; do
    IFS='|' read -r host elapsed speed <<< "${RESULTS[$name]}"
    echo "${SPEEDS[$name]}|${name}|${host}|${elapsed}|${speed}" >> "$tmp_file"
done

# 排序并输出
sort -t'|' -k1 -n "$tmp_file" | while IFS='|' read -r sort_key name host elapsed speed; do
    echo -e "  ${GREEN}✓${NC} ${name}"
    echo -e "    地址: ${host}"
    echo -e "    响应: ${elapsed} | 速度评级: ${speed}"
    echo ""
done

rm -f "$tmp_file"

# 输出推荐配置
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   推荐配置（daemon.json）${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 找出最快的 3 个
echo -e "${YELLOW}将以下内容添加到 Docker daemon 配置：${NC}"
echo ""
echo '```json'
echo '{'
echo '  "registry-mirrors": ['

# 输出前 3 个最快的
count=0
sort -t'|' -k1 -n "$tmp_file" 2>/dev/null | while IFS='|' read -r sort_key name host elapsed speed; do
    if [ $count -lt 3 ]; then
        comma=","
        if [ $count -eq 2 ]; then
            comma=""
        fi
        echo "    \"https://${host}\"${comma}"
        count=$((count + 1))
    fi
done

echo '  ]'
echo '}'
echo '```'
echo ""

# 输出 daemon.json 路径
echo -e "${YELLOW}配置文件位置：${NC}"
echo "  - Windows: C:\\ProgramData\\Docker\\config\\daemon.json"
echo "  - Linux: /etc/docker/daemon.json"
echo "  - macOS: ~/.docker/daemon.json"
echo ""

echo -e "${YELLOW}修改后重启 Docker：${NC}"
echo "  - Windows: 重启 Docker Desktop"
echo "  - Linux: sudo systemctl restart docker"
echo "  - macOS: 重启 Docker Desktop"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   使用建议${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. 优先使用响应时间 < 500ms 的镜像源"
echo "2. 配置多个镜像源作为备用"
echo "3. 定期测试（网络环境变化时）"
echo "4. 企业环境建议搭建私有 Registry"
echo ""