# R4900G3 Fan Controller / R4900G3 风扇控制器

This project provides a Python script to dynamically control the fan speeds of an H3C R4900G3 server based on CPU temperatures. It can be run directly or as a Docker container.

本项目提供一个 Python 脚本，用于根据 CPU 温度动态控制H3C R4900G3 服务器的风扇转速。可以直接运行，也可以作为 Docker 容器运行。

## Features / 特性

-   Monitors CPU temperatures via IPMI. / 通过 IPMI 监控 CPU 温度。
-   Adjusts fan speeds based on a configurable temperature curve. / 根据可配置的温度曲线调整风扇转速。
-   Separate fan control groups for different CPUs (configurable). / 可为不同 CPU 配置独立风扇控制组。
-   Fail-safe mode: sets fans to a default speed if temperature readings fail multiple times. / 故障安全模式：如果多次读取温度失败，则将风扇设置为默认转速。
-   Configurable via environment variables. / 可通过环境变量进行配置。
-   Can be run as a Docker container. / 可作为 Docker 容器运行。

## Requirements / 环境要求

### For Direct Execution / 直接运行

-   Python 3.6+ / Python 3.6+
-   `ipmitool` installed and accessible in PATH. / `ipmitool` 已安装并在系统 PATH 中。
    -   On Debian/Ubuntu: `sudo apt update && sudo apt install ipmitool`
    -   On CentOS/RHEL: `sudo yum install ipmitool`
-   Network access to the server's BMC/IPMI interface. / 对服务器 BMC/IPMI 接口的网络访问权限。

### For Docker Execution / Docker 运行

-   Docker installed. / Docker 已安装。
-   Network access to the server's BMC/IPMI interface from the Docker host. / Docker 主机对服务器 BMC/IPMI 接口的网络访问权限。

## Configuration / 配置项

The script is configured using environment variables. These are the same whether running directly or via Docker.

脚本通过环境变量进行配置。无论是直接运行还是通过 Docker 运行，这些变量都是相同的。

| Variable                      | Default Value (in script)                                                                 | Description (English)                                                                                                | 描述 (中文)                                                                                                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `IPMI_HOST`                   | `192.168.44.129`                                                                          | IP address or hostname of the BMC.                                                                                   | BMC 的 IP 地址或主机名。                                                                                                                      |
| `IPMI_USER`                   | `admin`                                                                                   | IPMI username.                                                                                                       | IPMI 用户名。                                                                                                                             |
| `IPMI_PASS`                   | `admin`                                                                                   | IPMI password.                                                                                                       | IPMI 密码。                                                                                                                               |
| `CPU1_FAN_IDS`                | `0,1,2`                                                                                   | Comma-separated list of fan IDs controlled by CPU1 temperature.                                                      | 由 CPU1 温度控制的风扇 ID 列表，以逗号分隔。                                                                                                        |
| `CPU2_FAN_IDS`                | `3,4,5`                                                                                   | Comma-separated list of fan IDs controlled by CPU2 temperature.                                                      | 由 CPU2 温度控制的风扇 ID 列表，以逗号分隔。                                                                                                        |
| `ALL_FAN_IDS_FAILSAFE`        | `0,1,2,3,4,5`                                                                             | Comma-separated list of all fan IDs to be controlled in fail-safe mode.                                              | 故障安全模式下控制的所有风扇 ID 列表，以逗号分隔。                                                                                                    |
| `MIN_FAN_SPEED`               | `20`                                                                                      | Minimum fan speed percentage (0-100).                                                                                | 最低风扇转速百分比 (0-100)。                                                                                                                    |
| `MAX_FAN_SPEED`               | `100`                                                                                     | Maximum fan speed percentage (0-100).                                                                                | 最高风扇转速百分比 (0-100)。                                                                                                                    |
| `DEFAULT_FAIL_SAFE_FAN_SPEED` | `75`                                                                                      | Fan speed percentage to set in fail-safe mode.                                                                       | 故障安全模式下设置的风扇转速百分比。                                                                                                                |
| `POLLING_INTERVAL_SECONDS`    | `5`                                                                                       | Interval in seconds between temperature checks.                                                                      | 温度检查之间的时间间隔（秒）。                                                                                                                      |
| `MAX_TEMP_READ_FAILURES`      | `5`                                                                                       | Number of consecutive temperature read failures before entering fail-safe mode.                                      | 进入故障安全模式前连续温度读取失败的次数。                                                                                                              |
| `FAN_CURVE_JSON`              | `'[{"temp": 50, "speed": 20}, {"temp": 60, "speed": 25}, {"temp": 70, "speed": 30}, {"temp": 75, "speed": 50}, {"temp": 80, "speed": 70}, {"temp": 85, "speed": 90}]'` | JSON string defining the temperature-to-fan-speed curve. Each object needs `temp` and `speed` keys. The curve is sorted by temperature and uses linear interpolation. | JSON 字符串，定义温度到风扇转速的曲线。每个对象需要 `temp` 和 `speed` 键。曲线按温度排序并使用线性插值。                                                                |

**Note on `FAN_CURVE_JSON`**:
The script uses linear interpolation between the points defined in the `FAN_CURVE_JSON`.
- If the current temperature is below the first point's temperature, the first point's speed is used.
- If the current temperature is above the last point's temperature, the last point's speed is used.
- Otherwise, speed is interpolated linearly between the two closest points.
All speeds are clamped between `MIN_FAN_SPEED` and `MAX_FAN_SPEED`.

**关于 `FAN_CURVE_JSON` 的说明**：
脚本在 `FAN_CURVE_JSON` 中定义的点之间使用线性插值。
- 如果当前温度低于第一个点的温度，则使用第一个点的转速。
- 如果当前温度高于最后一个点的温度，则使用最后一个点的转速。
- 否则，在两个最近的点之间线性插值计算转速。
所有转速都会被限制在 `MIN_FAN_SPEED` 和 `MAX_FAN_SPEED` 之间。

## Usage / 使用方法

### 1. Running with Docker (Recommended) / 使用 Docker 运行 (推荐)

This is the recommended way to run the controller as it bundles all dependencies.

这是推荐的运行方式，因为它打包了所有依赖项。

**a. Pull the image from Docker Hub / 从 Docker Hub 拉取镜像:**

```bash
docker pull rc0x01/r4900g3-fan-controller:latest
```

**b. Run the container / 运行容器:**

You **must** provide your IPMI credentials and host. Other variables are optional and will use defaults if not set.
The `--privileged` flag is often necessary for `ipmitool` to access the IPMI device. Alternatively, you might map `/dev/ipmi0` if your system is configured that way, but `--privileged` is generally more straightforward for this use case.

您 **必须** 提供 IPMI 凭据和主机地址。其他变量是可选的，如果未设置将使用默认值。
`--privileged` 标志通常是 `ipmitool` 访问 IPMI 设备所必需的。或者，如果您的系统配置如此，您可以映射 `/dev/ipmi0`，但对于此用例，`--privileged` 通常更直接。

```bash
docker run -d \
  --restart unless-stopped \
  --privileged \
  -e IPMI_HOST="your_bmc_ip_address" \
  -e IPMI_USER="your_ipmi_username" \
  -e IPMI_PASS="your_ipmi_password" \
  -e CPU1_FAN_IDS="0,1,2" \
  -e CPU2_FAN_IDS="3,4,5" \
  -e FAN_CURVE_JSON='[{"temp": 55, "speed": 25}, {"temp": 65, "speed": 40}, {"temp": 75, "speed": 60}, {"temp": 80, "speed": 85}]' \
  rc0x01/r4900g3-fan-controller:latest
```

To view logs:
查看日志：

```bash
docker logs <container_id_or_name> -f
```

### 2. Building the Docker Image Locally / 本地构建 Docker 镜像

If you prefer to build the image yourself:
如果您希望自己构建镜像：

```bash
git clone https://github.com/yourusername/R4900g3-fan-controller.git # Replace with your repo URL if applicable
cd R4900g3-fan-controller
docker build -t my-fan-controller .
```

Then run it as described above, replacing `rc0x01/r4900g3-fan-controller:latest` with `my-fan-controller`.
然后如上所述运行，将 `rc0x01/r4900g3-fan-controller:latest` 替换为 `my-fan-controller`。

### 3. Running Directly (without Docker) / 直接运行 (不使用 Docker)

**a. Clone the repository (if you haven't already) / 克隆仓库 (如果尚未克隆):**

```bash
git clone https://github.com/yourusername/R4900g3-fan-controller.git # Replace with your repo URL if applicable
cd R4900g3-fan-controller
```

**b. Install requirements / 安装依赖:**

Ensure Python 3 and `ipmitool` are installed (see [Requirements](#requirements--环境要求)).
There are no additional Python packages required beyond the standard library for the core script, but `ipmitool` is essential.

确保已安装 Python 3 和 `ipmitool` (参见 [Requirements](#requirements--环境要求))。
核心脚本除了标准库外不需要额外的 Python 包，但 `ipmitool` 是必需的。

**c. Set environment variables / 设置环境变量:**

```bash
export IPMI_HOST="your_bmc_ip_address"
export IPMI_USER="your_ipmi_username"
export IPMI_PASS="your_ipmi_password"
# Set other variables as needed, e.g.:
# export CPU1_FAN_IDS="0,1"
# export FAN_CURVE_JSON='[{"temp": 60, "speed": 30}, {"temp": 70, "speed": 50}]'
```

**d. Run the script / 运行脚本:**

```bash
python main.py
```

The script will log its activity to the console.
脚本会将其活动记录到控制台。

## Troubleshooting / 故障排除

-   **Cannot connect to IPMI host / 无法连接到 IPMI 主机:**
    -   Verify `IPMI_HOST` is correct. / 确认 `IPMI_HOST` 正确。
    -   Check network connectivity to the BMC (ping, firewall rules). / 检查到 BMC 的网络连接 (ping, 防火墙规则)。
    -   Ensure IPMI over LAN is enabled in BMC settings. / 确保 BMC 设置中启用了 IPMI over LAN。
-   **Authentication failure / 认证失败:**
    -   Verify `IPMI_USER` and `IPMI_PASS`. / 确认 `IPMI_USER` 和 `IPMI_PASS` 正确。
-   **`ipmitool` command not found (when running directly) / `ipmitool` 命令未找到 (直接运行时):**
    -   Ensure `ipmitool` is installed and in your system's PATH. / 确保 `ipmitool` 已安装并在系统 PATH 中。
-   **Permission denied (when running Docker without `--privileged` or direct run without `sudo` for `ipmitool` if needed):**
    -   `ipmitool` often requires root/privileged access to interact with the IPMI kernel device (e.g., `/dev/ipmi0`). For Docker, use `--privileged`. For direct execution, you might need to run the Python script with `sudo python main.py` if `ipmitool` requires it and your user doesn't have direct access, or configure `ipmitool` permissions appropriately. / `ipmitool` 通常需要 root/特权访问权限才能与 IPMI 内核设备 (例如 `/dev/ipmi0`) 交互。对于 Docker，请使用 `--privileged`。对于直接执行，如果 `ipmitool` 需要并且您的用户没有直接访问权限，您可能需要使用 `sudo python main.py` 运行 Python 脚本，或者适当配置 `ipmitool` 权限。

## License / 许可证

This project is licensed under the [GNU General Public License v3.0](LICENSE).
本项目采用 [GNU General Public License v3.0](LICENSE) 授权。
