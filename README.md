# R4900G3 Fan Controller

A Python script to dynamically control server fan speeds based on CPU temperatures using IPMI. Designed for H3C R4900G3 but adaptable for other IPMI-manageable servers. Best run as a Docker container.

## Features

-   Monitors CPU temperatures via IPMI.
-   Adjusts fan speeds based on a configurable temperature-to-speed curve.
-   **Flexible Fan Control Strategy**:
    -   `PER_CPU`: Default mode, CPU1 temperature controls fans in `CPU1_FAN_IDS`, CPU2 temperature controls fans in `CPU2_FAN_IDS`.
    -   `MAX_CPU_TEMP`: Uses the higher temperature of the two CPUs to set a unified speed for all fans listed in `CPU1_FAN_IDS` and `CPU2_FAN_IDS`.
-   Fail-safe mode: sets fans to a default speed if temperature readings fail.
-   Fully configurable via environment variables.
-   Dockerized for easy deployment.

## Running with Docker (Recommended)

**1. Pull from Docker Hub:**

```bash
docker pull rc0x01/r4900g3-fan-controller:latest
```

**2. Run the container:**

You **must** replace placeholder values for `IPMI_HOST`, `IPMI_USER`, and `IPMI_PASS` with your server's BMC credentials. The `--privileged` flag is typically required for `ipmitool` to access IPMI hardware.

```bash
docker run -d \
  --name fan-controller \
  --restart unless-stopped \
  --privileged \
  -e IPMI_HOST="your_bmc_ip_address" \
  -e IPMI_USER="your_ipmi_username" \
  -e IPMI_PASS="your_ipmi_password" \
  \
  # Optional: Fan Control Strategy (Default: PER_CPU)
  # Use MAX_CPU_TEMP to control all fans based on the hottest CPU
  -e FAN_CONTROL_STRATEGY="MAX_CPU_TEMP" \
  \
  # Optional: Fan Groupings (defaults are for a typical 6-fan setup)
  -e CPU1_FAN_IDS="0,1,2" \
  -e CPU2_FAN_IDS="3,4,5" \
  \
  # Optional: Fan Curve (see main.py for default if not set)
  # Example: -e FAN_CURVE_JSON='[{"temp": 40, "speed": 5},{"temp": 50, "speed": 10}, ...]' \
  \
  # Other optional parameters (see table below for defaults)
  -e MIN_FAN_SPEED="10" \
  -e MAX_FAN_SPEED="100" \
  -e DEFAULT_FAIL_SAFE_FAN_SPEED="75" \
  -e POLLING_INTERVAL_SECONDS="5" \
  -e MAX_TEMP_READ_FAILURES="5" \
  -e ALL_FAN_IDS_FAILSAFE="0,1,2,3,4,5" \
  \
  rc0x01/r4900g3-fan-controller:latest
```

To view logs: `docker logs fan-controller -f`

## Configuration Environment Variables

| Variable                      | Default (in script)                                                                                                | Description (English) / 描述 (中文)                                                                                                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `IPMI_HOST`                   | `192.168.44.129`                                                                                                   | IP address or hostname of the BMC. / BMC 的 IP 地址或主机名。                                                                                                                                          |
| `IPMI_USER`                   | `admin`                                                                                                            | IPMI username. / IPMI 用户名。                                                                                                                                                                     |
| `IPMI_PASS`                   | `admin`                                                                                                            | IPMI password. / IPMI 密码。                                                                                                                                                                     |
| `FAN_CONTROL_STRATEGY`        | `PER_CPU`                                                                                                          | Control strategy: `PER_CPU` (individual CPU control) or `MAX_CPU_TEMP` (unified control based on max CPU temp). / 控制策略：`PER_CPU` (独立CPU控制) 或 `MAX_CPU_TEMP` (基于最高CPU温度统一控制)。 |
| `CPU1_FAN_IDS`                | `0,1,2`                                                                                                            | Comma-separated fan IDs for CPU1 group (used by both strategies). / CPU1 风扇组的ID列表 (两种策略均使用)，逗号分隔。                                                                                             |
| `CPU2_FAN_IDS`                | `3,4,5`                                                                                                            | Comma-separated fan IDs for CPU2 group (used by both strategies). / CPU2 风扇组的ID列表 (两种策略均使用)，逗号分隔。                                                                                             |
| `ALL_FAN_IDS_FAILSAFE`        | `0,1,2,3,4,5`                                                                                                      | Fan IDs for fail-safe mode. / 故障安全模式下的风扇ID列表。                                                                                                                                               |
| `MIN_FAN_SPEED`               | `10` (Note: `main.py` default was `20`, Dockerfile `10`, using `10` from previous `docker run` example)             | Minimum fan speed percentage (0-100). / 最低风扇转速百分比。                                                                                                                                             |
| `MAX_FAN_SPEED`               | `100`                                                                                                              | Maximum fan speed percentage (0-100). / 最高风扇转速百分比。                                                                                                                                             |
| `DEFAULT_FAIL_SAFE_FAN_SPEED` | `75`                                                                                                               | Fan speed in fail-safe mode. / 故障安全模式下的转速。                                                                                                                                                    |
| `POLLING_INTERVAL_SECONDS`    | `5`                                                                                                                | Interval in seconds for temperature checks. / 温度检查间隔（秒）。                                                                                                                                         |
| `MAX_TEMP_READ_FAILURES`      | `5`                                                                                                                | Consecutive read failures before fail-safe. / 进入故障安全前的连续读取失败次数。                                                                                                                                |
| `FAN_CURVE_JSON`              | `'[{"temp": 40, "speed": 5},{"temp": 50, "speed": 10}, {"temp": 60, "speed": 30}, {"temp": 70, "speed": 25}, {"temp": 75, "speed": 50}, {"temp": 80, "speed": 70}, {"temp": 85, "speed": 90}]'` | JSON string for temperature-to-speed curve. Uses linear interpolation. / 定义温度到风扇转速曲线的JSON字符串。使用线性插值。                                                                              |

**Note on `MIN_FAN_SPEED` default:** The `main.py` script has a default of `20` if the environment variable is not set, while the `Dockerfile` and previous `docker run` examples used `10`. The table reflects `10` for consistency with typical `docker run` usage, but be aware of the script's internal default if the variable is entirely unset. The `docker run` example above explicitly sets it to `10`.

## Alternative: Building and Running Locally

If you prefer not to use Docker Hub:

1.  **Clone & Build:**
    ```bash
    # git clone <your-repo-url>
    # cd R4900g3-fan-controller
    docker build -t my-fan-controller .
    ```
2.  **Run:** Use the `docker run` command above, replacing `rc0x01/r4900g3-fan-controller:latest` with `my-fan-controller`.

For direct Python execution (without Docker), ensure `ipmitool` is installed and in your PATH, then set environment variables and run `python main.py`.

## Troubleshooting

-   **Connection/Authentication Issues:** Verify `IPMI_HOST`, `IPMI_USER`, `IPMI_PASS`, and network access to BMC. Ensure IPMI over LAN is enabled.
-   **`ipmitool` errors:** If running in Docker, ensure `--privileged` is used. If running directly, ensure `ipmitool` is installed and accessible.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
