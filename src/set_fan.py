import subprocess
import shlex

def set_fan_speed(ip_address, username, password, fan_id, speed_percentage):
    """
    使用 ipmitool 设置特定风扇的转速。

    参数:
        ip_address (str): BMC 的 IP 地址。
        username (str): IPMI 认证用户名。
        password (str): IPMI 认证密码。
        fan_id (int): 风扇ID (0-5)。
        speed_percentage (int): 风扇转速百分比 (0-100)。

    返回:
        tuple: 命令执行的 (返回码, 标准输出, 标准错误)。
               如果输入无效，则返回 (None, None, "无效的 fan_id 或 speed_percentage")。
    """
    if not (0 <= fan_id <= 5):
        print(f"错误: fan_id 必须在 0 到 5 之间。收到: {fan_id}")
        return None, None, "无效的 fan_id: 必须在 0 到 5 之间。"

    if not (0 <= speed_percentage <= 100):
        print(f"错误: speed_percentage 必须在 0 到 100 之间。收到: {speed_percentage}")
        return None, None, "无效的 speed_percentage: 必须在 0 到 100 之间。"

    # 将 fan_id 转换为十六进制字符串 (例如, 0 -> "0x00", 5 -> "0x05")
    fan_hex = f"0x{fan_id:02x}"

    # 将 speed_percentage (0-100) 转换为十六进制值 (0x00-0xff)
    # 原始命令中的 0x35 是十进制的 53。
    # 如果 100% 转速对应 0xFF (255), 则 speed_value = (speed_percentage / 100) * 255
    speed_value = int((speed_percentage / 100) * 255)
    speed_hex = f"0x{speed_value:02x}"

    # 原始命令: ipmitool -I lanplus -H 192.168.44.129 -U admin -P admin raw 0x36 0x03 0x20 0x14 0x00 0x01 0x00 0x35
    # 风扇 ID 是倒数第二个十六进制值 (示例中为 0x00)
    # 转速是最后一个十六进制值 (示例中为 0x35)
    command_parts = [
        "ipmitool",
        "-I", "lanplus",
        "-H", ip_address,
        "-U", username,
        "-P", password,
        "raw", "0x36", "0x03", "0x20", "0x14", "0x00", "0x01",
        fan_hex,  # 风扇ID
        "0x01",   # 固定字节
        speed_hex   # 风扇转速
    ]

    # 出于安全考虑，最好将命令作为参数列表传递给 subprocess.run,
    # 而不是使用 shell=True 的单个字符串。
    # shlex.join 可用于在需要时记录命令。
    print(f"执行命令: {' '.join(command_parts)}")

    try:
        # 如果密码可能包含shell元字符，请确保安全处理。
        # 此处直接列表传递通常更安全。
        process = subprocess.run(command_parts, capture_output=True, text=True, check=False)
        
        if process.returncode == 0:
            print(f"成功将风扇 {fan_id} 设置为 {speed_percentage}% 转速。")
            print(f"输出: {process.stdout}")
        else:
            print(f"设置风扇 {fan_id} 转速时出错。")
            print(f"返回码: {process.returncode}")
            print(f"标准输出: {process.stdout}")
            print(f"标准错误: {process.stderr}")
            
        return process.returncode, process.stdout, process.stderr
    except FileNotFoundError:
        print("错误: 未找到 ipmitool 命令。请确保已安装并在 PATH 中。")
        return None, None, "未找到 ipmitool 命令。"
    except Exception as e:
        print(f"发生意外错误: {e}")
        return None, None, str(e)

if __name__ == '__main__':
    # 示例用法 (请替换为您的实际 BMC 详细信息和所需设置)
    # 确保您已安装 ipmitool 并已为 BMC 配置 lanplus 访问。
    # 如果没有可访问的 BMC 和正确的凭据，此示例将无法运行。
    
    # --- 重要 ---
    # 测试时，请将这些占位符替换为您的实际 IPMI 详细信息。
    # 执行修改系统设置的命令时要小心。
    bmc_ip = "192.168.44.129"  # 替换为您的 BMC IP 地址
    bmc_user = "admin"    # 替换为您的 IPMI 用户名
    bmc_pass = "admin"  # 替换为您的 IPMI 密码

    # 测试用例 1: 设置风扇 0 为 50% 转速
    print("\n--- 测试用例 1: 设置风扇 0 为 50% ---")
    fan_to_set = 0
    speed_to_set = 50 
    # 对应 0x80 (128)
    # 预期命令部分: ... 0x00 0x01 0x80
    
    # ret_code, std_out, std_err = set_fan_speed(bmc_ip, bmc_user, bmc_pass, fan_to_set, speed_to_set)
    # if ret_code is not None:
    #     print(f"命令退出码: {ret_code}")
    #     if std_out:
    #         print(f"标准输出:\n{std_out}")
    #     if std_err:
    #         print(f"标准错误:\n{std_err}")
    # else:
    #     print("由于输入验证或其他预执行错误，函数调用失败。")

    # 测试用例 2: 设置风扇 3 为 21% 转速 (接近用户示例的 0x35)
    # 用户示例: 0x35 (十进制 53), 约占 255 的 20.8%
    # 使用 21% 以接近 0x35 ( (21/100)*255 = 53.55, int(53.55) = 53, hex(53) = 0x35)
    print("\n--- 测试用例 2: 设置风扇 3 为 21% (约 0x35) ---")
    fan_to_set = 3
    speed_to_set = 21 
    # (21/100)*255 = 53.55, int(53.55) = 53, hex(53) = 0x35
    # 预期命令部分: ... 0x03 0x01 0x35

    ret_code, std_out, std_err = set_fan_speed(bmc_ip, bmc_user, bmc_pass, fan_to_set, speed_to_set)
    if ret_code is not None:
        print(f"命令退出码: {ret_code}")
    else:
        print("函数调用失败。")

    # 测试用例 3: 无效的风扇 ID
    print("\n--- 测试用例 3: 无效的风扇 ID ---")
    # ret_code, std_out, std_err = set_fan_speed(bmc_ip, bmc_user, bmc_pass, 7, 50)
    # if ret_code is None and std_err:
    #    print(f"预期错误: {std_err}")


    # 测试用例 4: 无效的转速百分比
    print("\n--- 测试用例 4: 无效的转速百分比 ---")
    # ret_code, std_out, std_err = set_fan_speed(bmc_ip, bmc_user, bmc_pass, 1, 150)
    # if ret_code is None and std_err:
    #    print(f"预期错误: {std_err}")
    
    print("\n注意: 示例用法已注释掉。取消注释并替换占位符以进行测试。")
    print("确保 'ipmitool' 已安装，并且您的 BMC 可以使用提供的凭据进行访问。")
