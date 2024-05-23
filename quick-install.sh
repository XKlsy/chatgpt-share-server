#!/bin/bash
set -e
if [ "$(id -u)" != "0" ]; then
   echo "该脚本必须以 root 权限运行" 1>&2
   exit 1
fi

# 向 /etc/sysctl.conf 添加禁用 IPv6 的设置
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf

# 应用系统配置更改
sysctl -p

echo "IPv6 已禁用，并已应用更改。"
# 进入目录
cd /root/chatgpt-proxy-node

# 关闭 Docker 容器
docker compose down

# 删除所有 Docker 镜像
docker rmi -f $(docker images -q)

# 退出目录
cd ..

# 删除 chatgpt-proxy-node 文件夹
rm -rf /root/chatgpt-proxy-node
CURRENT_DIR=$(
    cd "$(dirname "$0")"
    pwd
)

function log() {
    message="[Proxy Log]: $1 "
    echo -e "${message}" 2>&1 | tee -a ${CURRENT_DIR}/glider-install.log
}


log "======================= 开始安装 ======================="

function Check_Root() {
  if [[ $EUID -ne 0 ]]; then
    echo "请使用 root 或 sudo 权限运行此脚本"
    exit 1
  fi
}


function Install_Docker(){
    if which docker >/dev/null 2>&1; then
        log "检测到 Docker 已安装，跳过安装步骤"
        log "启动 Docker "
        systemctl start docker 2>&1 | tee -a ${CURRENT_DIR}/install.log
    else
        log "... 在线安装 docker"

        if [[ $(curl -s ipinfo.io/country) == "CN" ]]; then
            sources=(
                "https://mirrors.aliyun.com/docker-ce"
                "https://mirrors.tencent.com/docker-ce"
                "https://mirrors.163.com/docker-ce"
                "https://mirrors.cernet.edu.cn/docker-ce"
            )

            get_average_delay() {
                local source=$1
                local total_delay=0
                local iterations=3

                for ((i = 0; i < iterations; i++)); do
                    delay=$(curl -o /dev/null -s -w "%{time_total}\n" "$source")
                    total_delay=$(awk "BEGIN {print $total_delay + $delay}")
                done

                average_delay=$(awk "BEGIN {print $total_delay / $iterations}")
                echo "$average_delay"
            }

            min_delay=${#sources[@]}
            selected_source=""

            for source in "${sources[@]}"; do
                average_delay=$(get_average_delay "$source")

                if (( $(awk 'BEGIN { print '"$average_delay"' < '"$min_delay"' }') )); then
                    min_delay=$average_delay
                    selected_source=$source
                fi
            done

            if [ -n "$selected_source" ]; then
                echo "选择延迟最低的源 $selected_source，延迟为 $min_delay 秒"
                export DOWNLOAD_URL="$selected_source"
                curl -fsSL "https://get.docker.com" -o get-docker.sh
                sh get-docker.sh 2>&1 | tee -a ${CURRENT_DIR}/install.log

                log "... 启动 docker"
                systemctl enable docker; systemctl daemon-reload; systemctl start docker 2>&1 | tee -a ${CURRENT_DIR}/install.log

                docker_config_folder="/etc/docker"
                if [[ ! -d "$docker_config_folder" ]];then
                    mkdir -p "$docker_config_folder"
                fi

                docker version >/dev/null 2>&1
                if [[ $? -ne 0 ]]; then
                    log "docker 安装失败"
                    exit 1
                else
                    log "docker 安装成功"
                fi
            else
                log "无法选择源进行安装"
                exit 1
            fi
        else
            log "非中国大陆地区，无需更改源"
            export DOWNLOAD_URL="https://download.docker.com"
            curl -fsSL "https://get.docker.com" -o get-docker.sh
            sh get-docker.sh 2>&1 | tee -a ${CURRENT_DIR}/install.log

            log "... 启动 docker"
            systemctl enable docker; systemctl daemon-reload; systemctl start docker 2>&1 | tee -a ${CURRENT_DIR}/install.log

            docker_config_folder="/etc/docker"
            if [[ ! -d "$docker_config_folder" ]];then
                mkdir -p "$docker_config_folder"
            fi

            docker version >/dev/null 2>&1
            if [[ $? -ne 0 ]]; then
                log "docker 安装失败"
                exit 1
            else
                log "docker 安装成功"
            fi
        fi
    fi
}

function Install_Compose(){
    docker-compose version >/dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        log "... 在线安装 docker-compose"
        
        arch=$(uname -m)
		if [ "$arch" == 'armv7l' ]; then
			arch='armv7'
		fi
		curl -L https://resource.fit2cloud.com/docker/compose/releases/download/v2.22.0/docker-compose-$(uname -s | tr A-Z a-z)-$arch -o /usr/local/bin/docker-compose 2>&1 | tee -a ${CURRENT_DIR}/install.log
        if [[ ! -f /usr/local/bin/docker-compose ]];then
            log "docker-compose 下载失败，请稍候重试"
            exit 1
        fi
        chmod +x /usr/local/bin/docker-compose
        ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

        docker-compose version >/dev/null 2>&1
        if [[ $? -ne 0 ]]; then
            log "docker-compose 安装失败"
            exit 1
        else
            log "docker-compose 安装成功"
        fi
    else
        compose_v=`docker-compose -v`
        if [[ $compose_v =~ 'docker-compose' ]];then
            read -p "检测到已安装 Docker Compose 版本较低（需大于等于 v2.0.0 版本），是否升级 [y/n] : " UPGRADE_DOCKER_COMPOSE
            if [[ "$UPGRADE_DOCKER_COMPOSE" == "Y" ]] || [[ "$UPGRADE_DOCKER_COMPOSE" == "y" ]]; then
                rm -rf /usr/local/bin/docker-compose /usr/bin/docker-compose
                Install_Compose
            else
                log "Docker Compose 版本为 $compose_v，可能会影响应用商店的正常使用"
            fi
        else
            log "检测到 Docker Compose 已安装，跳过安装步骤"
        fi
    fi
}
cd product/chatgpt-share
docker compose down
cd ..
rm -rf chatgpt-share
cd ..
cd chatgpt-share
docker compose down
cd ..
rm -rf chatgpt-share
## 克隆仓库到本地
mkdir product
cd product
echo "clone repository..."
git clone -b deploy  --depth=1 https://github.com/XKlsy/chatgpt-share-server.git chatgpt-share
## 进入目录
cd chatgpt-share
curl -sSfL https://raw.githubusercontent.com/simkinhu/xyhelpercarlist/master/quick-install/quick-list.sh | bash

docker compose pull
docker compose up -d --remove-orphans

## 提示信息
echo "服务启动成功，请访问 http://localhost:8300"
echo "管理员后台地址 http://localhost:8300/xyhelper"
echo "管理员账号: admin"
echo "管理员密码: 123456"
echo "请及时修改管理员密码"
