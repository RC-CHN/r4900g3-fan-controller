import os
import time
import logging
import json # 用于解析环境变量中的 FAN_CURVE
from src.get_temp import get_cpu_temperatures
from src.set_fan import set_fan_speed

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- IPMI 配置 ---
IPMI_HOST = os.environ.get("IPMI_HOST", "192.168.44.129")
IPMI_USER = os.environ.get("IPMI_USER", "admin")
IPMI_PASS = os.environ.get("IPMI_PASS", "admin")

# --- 风扇控制策略 ---
# FAN_CONTROL_STRATEGY: "PER_CPU" (默认) 或 "MAX_CPU_TEMP"
# PER_CPU: 每个CPU温度分别控制其指定的风扇组
# MAX_CPU_TEMP: 使用两个CPU中较高的温度控制所有指定风扇 (CPU1_FAN_IDS + CPU2_FAN_IDS)
FAN_CONTROL_STRATEGY = os.environ.get("FAN_CONTROL_STRATEGY", "PER_CPU").upper()
VALID_FAN_CONTROL_STRATEGIES = ["PER_CPU", "MAX_CPU_TEMP"]
if FAN_CONTROL_STRATEGY not in VALID_FAN_CONTROL_STRATEGIES:
    logging.warning(f"无效的风扇控制策略 '{FAN_CONTROL_STRATEGY}'。将使用默认策略 'PER_CPU'。")
    FAN_CONTROL_STRATEGY = "PER_CPU"

# --- 风扇及控制逻辑配置 ---
# 风扇分组配置
raw_cpu1_fan_ids = os.environ.get("CPU1_FAN_IDS", "0,1,2")
raw_cpu2_fan_ids = os.environ.get("CPU2_FAN_IDS", "3,4,5")
ALL_POSSIBLE_FAN_IDS_DEFAULT_STR = "0,1,2,3,4,5" # 用于故障安全模式

try:
    CPU1_FAN_IDS = [int(fid.strip()) for fid in raw_cpu1_fan_ids.split(',') if fid.strip()]
    if not CPU1_FAN_IDS and raw_cpu1_fan_ids: # 处理空字符串或只有逗号的情况
        raise ValueError("CPU1_FAN_IDS 环境变量解析后为空列表")
except ValueError as e:
    logging.warning(f"解析 CPU1_FAN_IDS ('{raw_cpu1_fan_ids}') 失败: {e}. 使用默认值 [0, 1, 2].")
    CPU1_FAN_IDS = [0, 1, 2]

try:
    CPU2_FAN_IDS = [int(fid.strip()) for fid in raw_cpu2_fan_ids.split(',') if fid.strip()]
    if not CPU2_FAN_IDS and raw_cpu2_fan_ids:
        raise ValueError("CPU2_FAN_IDS 环境变量解析后为空列表")
except ValueError as e:
    logging.warning(f"解析 CPU2_FAN_IDS ('{raw_cpu2_fan_ids}') 失败: {e}. 使用默认值 [3, 4, 5].")
    CPU2_FAN_IDS = [3, 4, 5]

# 用于故障安全模式下控制所有可能的风扇
try:
    ALL_POSSIBLE_FAN_IDS = [int(fid.strip()) for fid in os.environ.get("ALL_FAN_IDS_FAILSAFE", ALL_POSSIBLE_FAN_IDS_DEFAULT_STR).split(',') if fid.strip()]
    if not ALL_POSSIBLE_FAN_IDS:
        raise ValueError("ALL_FAN_IDS_FAILSAFE 解析后为空列表")
except ValueError as e:
    logging.warning(f"解析 ALL_FAN_IDS_FAILSAFE 失败: {e}. 使用默认值 [0, 1, 2, 3, 4, 5].")
    ALL_POSSIBLE_FAN_IDS = list(range(6))


MIN_FAN_SPEED = int(os.environ.get("MIN_FAN_SPEED", "20"))
MAX_FAN_SPEED = int(os.environ.get("MAX_FAN_SPEED", "100"))
DEFAULT_FAIL_SAFE_FAN_SPEED = int(os.environ.get("DEFAULT_FAIL_SAFE_FAN_SPEED", "75"))
POLLING_INTERVAL_SECONDS = int(os.environ.get("POLLING_INTERVAL_SECONDS", "5"))
MAX_TEMP_READ_FAILURES = int(os.environ.get("MAX_TEMP_READ_FAILURES", "5"))

# 风扇控制曲线 (温度阈值: 转速百分比)
# 环境变量 FAN_CURVE_JSON 应为 JSON 字符串，例如:
# '[{"temp": 40, "speed": 25}, {"temp": 50, "speed": 35}]'
# 注意: JSON 中的键必须是 "temp" 和 "speed"。
# 内部存储时，我们将其转换为元组列表: [(temp_threshold, speed_percentage), ...]
# 更新默认风扇曲线策略：70度以下低转速，70度以上再大幅拉升
DEFAULT_FAN_CURVE_STR = '[{"temp": 40, "speed": 5},{"temp": 50, "speed": 10}, {"temp": 60, "speed": 30}, {"temp": 70, "speed": 25}, {"temp": 75, "speed": 50}, {"temp": 80, "speed": 70}, {"temp": 85, "speed": 90}]'
fan_curve_json_str = os.environ.get("FAN_CURVE_JSON", DEFAULT_FAN_CURVE_STR)
try:
    fan_curve_data = json.loads(fan_curve_json_str)
    FAN_CURVE = sorted([(item['temp'], item['speed']) for item in fan_curve_data if 'temp' in item and 'speed' in item])
    if not FAN_CURVE and fan_curve_data: # JSON有效但内容不符合预期格式
        raise ValueError("FAN_CURVE_JSON 解析成功，但未找到有效的 'temp'/'speed' 对。")
    if not FAN_CURVE and not fan_curve_data and fan_curve_json_str != DEFAULT_FAN_CURVE_STR : # 用户提供了空JSON
         logging.warning(f"FAN_CURVE_JSON ('{fan_curve_json_str}') 解析为空，将使用硬编码的默认曲线。")
         fan_curve_data = json.loads(DEFAULT_FAN_CURVE_STR) # 重新加载默认值
         FAN_CURVE = sorted([(item['temp'], item['speed']) for item in fan_curve_data])

except (json.JSONDecodeError, TypeError, ValueError) as e:
    logging.warning(f"解析 FAN_CURVE_JSON ('{fan_curve_json_str}') 失败: {e}. 使用硬编码的默认曲线.")
    # 使用硬编码的默认值以防万一
    FAN_CURVE = [
        (50, 20), (60, 25), (70, 30), (75, 50), (80, 70), (85, 90)
    ]
# 如果温度 >= 最后一个阈值, 则使用 MAX_FAN_SPEED

def get_target_fan_speed(current_temp):
    """根据当前温度和风扇曲线通过线性插值计算目标风扇转速"""
    if current_temp is None:
        logging.warning("当前温度未知，无法计算目标转速。")
        return None

    if not FAN_CURVE:
        logging.warning("风扇曲线未定义或为空，无法计算目标转速。返回最低转速。")
        return MIN_FAN_SPEED

    # FAN_CURVE 已经按温度升序排序
    
    # 情况 1: 当前温度低于或等于第一个曲线点的温度
    if current_temp <= FAN_CURVE[0][0]:
        target_speed = FAN_CURVE[0][1]
        logging.debug(f"温度 {current_temp}°C <= 第一个阈值 {FAN_CURVE[0][0]}°C. 转速: {target_speed}%")
        return max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, int(round(target_speed))))

    # 情况 2: 当前温度高于或等于最后一个曲线点的温度
    if current_temp >= FAN_CURVE[-1][0]:
        target_speed = FAN_CURVE[-1][1]
        logging.debug(f"温度 {current_temp}°C >= 最后一个阈值 {FAN_CURVE[-1][0]}°C. 转速: {target_speed}%")
        return max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, int(round(target_speed))))

    # 情况 3: 当前温度在两个曲线点之间，进行线性插值
    for i in range(len(FAN_CURVE) - 1):
        t1, s1 = FAN_CURVE[i]
        t2, s2 = FAN_CURVE[i+1]

        if t1 <= current_temp < t2:
            # 避免除以零 (虽然排序后 t2 应该总是大于 t1)
            if t1 == t2: # 如果两个点温度相同，取较低的转速或平均值，这里取s1
                target_speed = s1
            else:
                # 线性插值公式: S = S1 + (当前温度 - T1) * (S2 - S1) / (T2 - T1)
                target_speed = s1 + (current_temp - t1) * (s2 - s1) / (t2 - t1)
            
            logging.debug(f"温度 {current_temp}°C 在 {t1}°C (转速 {s1}%) 和 {t2}°C (转速 {s2}%) 之间. 插值转速: {target_speed:.2f}%")
            # 四舍五入到最近的整数
            target_speed_int = int(round(target_speed))
            return max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, target_speed_int))
            
    # 理论上不应该执行到这里，因为上面的情况覆盖了所有可能。
    # 但作为备用，如果出现意外情况（例如FAN_CURVE只有一个点且不匹配前两种情况），
    # 返回最后一个点的速度或最低速度。
    logging.warning(f"在风扇曲线中未找到合适的插值区间 (温度: {current_temp}°C)。使用最后一个已知点或最低转速。")
    return max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, int(round(FAN_CURVE[-1][1]))))


def main():
    logging.info("启动风扇控制器...")
    logging.info(f"IPMI Host: {IPMI_HOST}")
    logging.info(f"CPU1 控制的风扇 IDs: {CPU1_FAN_IDS}")
    logging.info(f"CPU2 控制的风扇 IDs: {CPU2_FAN_IDS}")
    logging.info(f"风扇控制策略: {FAN_CONTROL_STRATEGY}")
    logging.info(f"故障安全时控制的风扇 IDs: {ALL_POSSIBLE_FAN_IDS}")
    logging.info(f"轮询间隔: {POLLING_INTERVAL_SECONDS} 秒")
    logging.info(f"风扇曲线 (temp°C, speed%): {FAN_CURVE}")
    logging.info(f"最低转速: {MIN_FAN_SPEED}%, 最高转速: {MAX_FAN_SPEED}%")

    temp_read_failures = 0

    while True:
        try:
            cpu_temps = get_cpu_temperatures(IPMI_HOST, IPMI_USER, IPMI_PASS)
            cpu1_temp = cpu_temps.get("CPU1_Temp")
            cpu2_temp = cpu_temps.get("CPU2_Temp")

            logging.info(f"获取到的温度 - CPU1: {cpu1_temp}°C, CPU2: {cpu2_temp}°C")

            applied_any_speed = False

            if cpu1_temp is None and cpu2_temp is None:
                logging.error("未能获取任何有效的 CPU 温度。")
                temp_read_failures += 1
            else:
                temp_read_failures = 0 # 成功读取至少一个温度，重置失败计数器

                if FAN_CONTROL_STRATEGY == "MAX_CPU_TEMP":
                    control_temp = None
                    if cpu1_temp is not None and cpu2_temp is not None:
                        control_temp = max(cpu1_temp, cpu2_temp)
                        logging.info(f"MAX_CPU_TEMP策略: CPU1={cpu1_temp}°C, CPU2={cpu2_temp}°C. 使用控制温度: {control_temp}°C")
                    elif cpu1_temp is not None:
                        control_temp = cpu1_temp
                        logging.info(f"MAX_CPU_TEMP策略: 仅CPU1温度有效 ({cpu1_temp}°C). 使用控制温度: {control_temp}°C")
                    elif cpu2_temp is not None:
                        control_temp = cpu2_temp
                        logging.info(f"MAX_CPU_TEMP策略: 仅CPU2温度有效 ({cpu2_temp}°C). 使用控制温度: {control_temp}°C")
                    else:
                        # 此情况已在外部 if cpu1_temp is None and cpu2_temp is None: 处理
                        pass 
                    
                    if control_temp is not None:
                        target_speed_unified = get_target_fan_speed(control_temp)
                        if target_speed_unified is not None:
                            all_controlled_fans = list(set(CPU1_FAN_IDS + CPU2_FAN_IDS)) # 合并并去重
                            if not all_controlled_fans:
                                logging.warning("MAX_CPU_TEMP策略: CPU1_FAN_IDS 和 CPU2_FAN_IDS 都为空，没有风扇可控制。")
                            else:
                                logging.info(f"MAX_CPU_TEMP策略: 控制温度 {control_temp}°C, 统一目标转速: {target_speed_unified}% (风扇: {all_controlled_fans})")
                                for fan_id in all_controlled_fans:
                                    ret_code, _, std_err = set_fan_speed(IPMI_HOST, IPMI_USER, IPMI_PASS, fan_id, target_speed_unified)
                                    if ret_code != 0:
                                        logging.error(f"设置风扇 {fan_id} (统一控制) 转速为 {target_speed_unified}% 失败。错误: {std_err}")
                                    else:
                                        logging.info(f"成功设置风扇 {fan_id} (统一控制) 转速为 {target_speed_unified}%")
                                applied_any_speed = True
                        else:
                             logging.warning(f"MAX_CPU_TEMP策略: 控制温度 {control_temp}°C, 但未能计算出统一目标转速。")
                
                elif FAN_CONTROL_STRATEGY == "PER_CPU":
                    # 处理 CPU1 的风扇 (原有逻辑)
                    if cpu1_temp is not None and CPU1_FAN_IDS:
                        target_speed_cpu1 = get_target_fan_speed(cpu1_temp)
                        if target_speed_cpu1 is not None:
                            logging.info(f"PER_CPU策略: CPU1 温度 {cpu1_temp}°C, 目标转速: {target_speed_cpu1}% (风扇: {CPU1_FAN_IDS})")
                            for fan_id in CPU1_FAN_IDS:
                                ret_code, _, std_err = set_fan_speed(IPMI_HOST, IPMI_USER, IPMI_PASS, fan_id, target_speed_cpu1)
                                if ret_code != 0:
                                    logging.error(f"设置风扇 {fan_id} (CPU1组) 转速为 {target_speed_cpu1}% 失败。错误: {std_err}")
                                else:
                                    logging.info(f"成功设置风扇 {fan_id} (CPU1组) 转速为 {target_speed_cpu1}%")
                            applied_any_speed = True
                    elif CPU1_FAN_IDS: # CPU1_Temp is None but fans are assigned
                        logging.warning(f"PER_CPU策略: CPU1 温度未获取到，但已分配风扇 {CPU1_FAN_IDS}。这些风扇将不会基于CPU1温度调整。")

                    # 处理 CPU2 的风扇 (原有逻辑)
                    if cpu2_temp is not None and CPU2_FAN_IDS:
                        target_speed_cpu2 = get_target_fan_speed(cpu2_temp)
                        if target_speed_cpu2 is not None:
                            logging.info(f"PER_CPU策略: CPU2 温度 {cpu2_temp}°C, 目标转速: {target_speed_cpu2}% (风扇: {CPU2_FAN_IDS})")
                            for fan_id in CPU2_FAN_IDS:
                                ret_code, _, std_err = set_fan_speed(IPMI_HOST, IPMI_USER, IPMI_PASS, fan_id, target_speed_cpu2)
                                if ret_code != 0:
                                    logging.error(f"设置风扇 {fan_id} (CPU2组) 转速为 {target_speed_cpu2}% 失败。错误: {std_err}")
                                else:
                                    logging.info(f"成功设置风扇 {fan_id} (CPU2组) 转速为 {target_speed_cpu2}%")
                            applied_any_speed = True
                    elif CPU2_FAN_IDS: # CPU2_Temp is None but fans are assigned
                        logging.warning(f"PER_CPU策略: CPU2 温度未获取到，但已分配风扇 {CPU2_FAN_IDS}。这些风扇将不会基于CPU2温度调整。")
                
                # 通用检查：是否应用了任何速度
                if not applied_any_speed and (cpu1_temp is not None or cpu2_temp is not None):
                    logging.warning("获取到有效温度，但没有风扇被成功设置转速（可能风扇组为空、目标转速计算失败或控制策略未覆盖）。")

            if temp_read_failures >= MAX_TEMP_READ_FAILURES:
                logging.critical(f"连续 {temp_read_failures} 次读取所有相关 CPU 温度失败！进入故障安全模式，为所有已知的风扇 ({ALL_POSSIBLE_FAN_IDS}) 设置转速为 {DEFAULT_FAIL_SAFE_FAN_SPEED}%")
                for fan_id in ALL_POSSIBLE_FAN_IDS: # 使用 ALL_POSSIBLE_FAN_IDS
                    set_fan_speed(IPMI_HOST, IPMI_USER, IPMI_PASS, fan_id, DEFAULT_FAIL_SAFE_FAN_SPEED)
                # 可以在这里添加更复杂的报警逻辑

        except Exception as e:
            logging.exception(f"主循环发生意外错误: {e}")
            temp_read_failures += 1 # 将未知错误也视为读取失败的一种
            if temp_read_failures >= MAX_TEMP_READ_FAILURES:
                 logging.critical(f"因异常导致连续 {temp_read_failures} 次失败！进入故障安全模式，为所有已知的风扇 ({ALL_POSSIBLE_FAN_IDS}) 设置转速为 {DEFAULT_FAIL_SAFE_FAN_SPEED}%")
                 for fan_id in ALL_POSSIBLE_FAN_IDS: # 使用 ALL_POSSIBLE_FAN_IDS
                    set_fan_speed(IPMI_HOST, IPMI_USER, IPMI_PASS, fan_id, DEFAULT_FAIL_SAFE_FAN_SPEED)

        time.sleep(POLLING_INTERVAL_SECONDS)

if __name__ == '__main__':
    # 确保在执行前替换 IPMI 环境变量或脚本中的默认值
    # 例如:
    # export IPMI_HOST="your_bmc_ip"
    # export CPU1_FAN_IDS="0,1"
    # export CPU2_FAN_IDS="2,3,4,5"
    # export IPMI_USER="your_user"
    # export IPMI_PASS="your_password"
    # python main.py
    main()
