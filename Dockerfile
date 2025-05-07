# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装 ipmitool
# RUN apt-get update && apt-get install -y ipmitool && rm -rf /var/lib/apt/lists/*
# 注意: 上述命令适用于基于 Debian/Ubuntu 的镜像。
# 如果基础镜像不同 (例如 Alpine)，则需要使用相应的包管理器 (例如 apk add ipmitool)。
# 为了更广泛的兼容性和更小的镜像体积，可以考虑多阶段构建或寻找包含 ipmitool 的特定基础镜像，
# 但对于大多数情况，python:slim 配合 apt-get 是一个不错的起点。
# 这里我们先注释掉，因为执行 apt-get update 可能会比较耗时，
# 并且用户可能需要根据其基础镜像或网络环境调整。
# 实际使用时，请取消注释并确保其能正确执行。
# 暂时我们假设 ipmitool 会在运行时环境或通过其他方式提供。
# 如果您希望 Docker 镜像自带 ipmitool，请取消下面这行的注释：
RUN apt-get update && \
    apt-get install -y ipmitool && \
    rm -rf /var/lib/apt/lists/*

# 将当前目录内容复制到容器的 /app 目录
COPY . /app

# 设置环境变量 (推荐在 docker run 命令中覆盖这些值)
# 这些是 IPMI 连接凭据的占位符
ENV IPMI_HOST="your_bmc_ip_address"
ENV IPMI_USER="your_ipmi_username"
ENV IPMI_PASS="your_ipmi_password"

# 这些是风扇控制参数的占位符/默认值示例
# 用户可以在 docker run 时通过 -e 选项覆盖它们
# 风扇ID由CPU1温度控制
ENV CPU1_FAN_IDS="0,1,2"
# 风扇ID由CPU2温度控制
ENV CPU2_FAN_IDS="3,4,5"
# 故障安全模式下控制的风扇ID
ENV ALL_FAN_IDS_FAILSAFE="0,1,2,3,4,5"
ENV MIN_FAN_SPEED="20"
ENV MAX_FAN_SPEED="100"
ENV DEFAULT_FAIL_SAFE_FAN_SPEED="75"
ENV POLLING_INTERVAL_SECONDS="15"
ENV MAX_TEMP_READ_FAILURES="5"
# FAN_CURVE_JSON 的默认值在 main.py 中定义，这里仅作示例
# ENV FAN_CURVE_JSON='[{"temp": 40, "speed": 25}, {"temp": 50, "speed": 35}, {"temp": 60, "speed": 50}, {"temp": 70, "speed": 75}, {"temp": 75, "speed": 90}]'

# 当容器启动时运行 main.py
CMD ["python", "main.py"]
