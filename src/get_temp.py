import subprocess
import re
import shlex

def _parse_sensor_temperature(output_text):
    """
    从 ipmitool sensor get 命令的输出中解析温度。
    期望的行格式: "Sensor Reading        : XX (+/- Y) degrees C"
    """
    match = re.search(r"Sensor Reading\s*:\s*([\d\.-]+)", output_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            print(f"错误: 无法将解析出的温度值 '{match.group(1)}' 转换为浮点数。")
            return None
    else:
        # 尝试匹配另一种可能的输出格式，例如某些传感器可能只报告整数
        match_alt = re.search(r"Sensor Reading\s*:\s*(\d+)\s*degrees C", output_text)
        if match_alt:
            try:
                return float(match_alt.group(1))
            except ValueError:
                print(f"错误: 无法将解析出的备用温度值 '{match_alt.group(1)}' 转换为浮点数。")
                return None
        print(f"错误: 在输出中未找到 'Sensor Reading'。输出:\n{output_text}")
        return None

def _get_single_sensor_value(ip_address, username, password, sensor_name):
    """
    获取单个 IPMI 传感器的值并解析。
    """
    command_parts = [
        "ipmitool",
        "-I", "lanplus",
        "-H", ip_address,
        "-U", username,
        "-P", password,
        "sensor", "get", sensor_name
    ]
    print(f"执行命令: {' '.join(command_parts)}")
    try:
        process = subprocess.run(command_parts, capture_output=True, text=True, check=False)
        if process.returncode == 0:
            return _parse_sensor_temperature(process.stdout)
        else:
            print(f"错误: 执行 ipmitool 命令失败 (传感器: {sensor_name})。返回码: {process.returncode}")
            print(f"标准输出:\n{process.stdout}")
            print(f"标准错误:\n{process.stderr}")
            return None
    except FileNotFoundError:
        print("错误: 未找到 ipmitool 命令。请确保已安装并在 PATH 中。")
        return None
    except Exception as e:
        print(f"获取传感器 {sensor_name} 时发生意外错误: {e}")
        return None

def get_cpu_temperatures(ip_address, username, password):
    """
    获取 CPU1 和 CPU2 的温度。

    参数:
        ip_address (str): BMC 的 IP 地址。
        username (str): IPMI 认证用户名。
        password (str): IPMI 认证密码。

    返回:
        dict: 包含 CPU 温度的字典, 例如 {'CPU1_Temp': 55.0, 'CPU2_Temp': 49.0}。
              如果获取失败，对应的值可能为 None。
    """
    temperatures = {}
    
    cpu1_temp = _get_single_sensor_value(ip_address, username, password, "CPU1_Temp")
    temperatures["CPU1_Temp"] = cpu1_temp
    
    cpu2_temp = _get_single_sensor_value(ip_address, username, password, "CPU2_Temp")
    temperatures["CPU2_Temp"] = cpu2_temp
    
    return temperatures

if __name__ == '__main__':
    # --- 重要 ---
    # 测试时，请将这些占位符替换为您的实际 IPMI 详细信息。
    # 执行修改系统设置的命令时要小心。
    bmc_ip = "192.168.44.129"  # 使用您之前提供的 IP
    bmc_user = "admin"         # 使用您之前提供的用户名
    bmc_pass = "admin"         # 使用您之前提供的密码

    print(f"\n--- 测试: 获取 CPU 温度 ({bmc_ip}) ---")
    cpu_temps = get_cpu_temperatures(bmc_ip, bmc_user, bmc_pass)

    if cpu_temps:
        print("\n获取到的 CPU 温度:")
        for sensor, temp in cpu_temps.items():
            if temp is not None:
                print(f"  {sensor}: {temp}°C")
            else:
                print(f"  {sensor}: 未能获取温度")
    else:
        print("未能获取任何 CPU 温度信息。")

    # 示例: 测试无效的传感器名称 (预期会失败或返回 None)
    # print("\n--- 测试: 获取无效传感器 ---")
    # invalid_temp = _get_single_sensor_value(bmc_ip, bmc_user, bmc_pass, "NON_EXISTENT_SENSOR")
    # if invalid_temp is None:
    #     print("成功处理无效传感器名称 (返回 None)。")
    # else:
    #     print(f"警告: 无效传感器获取到值: {invalid_temp}")

    # 示例: 测试解析各种输出
    # print("\n--- 测试: 解析器测试 ---")
    # test_output_ok = "Sensor Reading        : 55.0 (+/- 0) degrees C"
    # print(f"解析 '{test_output_ok}': {_parse_sensor_temperature(test_output_ok)}")
    # test_output_negative = "Sensor Reading        : -5.0 (+/- 0) degrees C"
    # print(f"解析 '{test_output_negative}': {_parse_sensor_temperature(test_output_negative)}")
    # test_output_no_decimal = "Sensor Reading        : 60 degrees C" # 假设的简化输出
    # print(f"解析 '{test_output_no_decimal}': {_parse_sensor_temperature(test_output_no_decimal)}")
    # test_output_fail = "Some other random text"
    # print(f"解析 '{test_output_fail}': {_parse_sensor_temperature(test_output_fail)}")
