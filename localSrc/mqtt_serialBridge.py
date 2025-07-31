import serial
import time
import paho.mqtt.client as mqtt
import redis
import threading

# 串口初始化
ser = serial.Serial('COM2', 57600, timeout=0.1)

# 连接 Redis（服务器地址）
r = redis.Redis(host="192.168.83.228", port=6379, decode_responses=True)


# 初始化串口通信：MCU置位
def send_mode_sequence():
    print("初始化，MCU置位")
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.3)

    for _ in range(5):
        ser.write(bytes([0xDE]))  # 速度模式
        time.sleep(0.2)
    for _ in range(5):
        ser.write(bytes([0xEA]))  # 0xEA是开环模式，0xEB是闭环模式
        time.sleep(0.2)
    ser.write(bytes([0xEE]))  # 启动电机
    time.sleep(1)
    print("初始化完成")


# 串口下发控制量
def send_pwm_value(pwm_str):
    for ch in pwm_str:
        ser.write(bytes([ord(ch)]))
        time.sleep(0.15)
    print(f"[串口] 已发送 PWM 控制量: {pwm_str}")

    # 追加写入控制量日志
    with open("pwm_log.txt", "a") as pwm_log:
        pwm_log.write(f"{int(pwm_str)}\n")


# MQTT回调
def on_connect(client, userdata, flags, rc):
    print("MQTT已连接，返回码:", rc)
    client.subscribe("control/u")


def on_message(client, userdata, msg):
    pwm_str = msg.payload.decode()
    print(f"[MQTT] 接收到控制量：{pwm_str}")
    if len(pwm_str) == 3 and pwm_str.isdigit():
        send_pwm_value(pwm_str)


# 串口读取线程：读取数据帧 FF xx xx，并写入 Redis
def read_serial_loop():
    buffer = bytearray()
    with open("rpm_log.txt", "a") as f:  # 追加写入模式
        while True:
            if ser.in_waiting:
                buffer += ser.read(ser.in_waiting)

            # 检查并解析完整帧
            while len(buffer) >= 3:
                if buffer[0] == 0xFF:
                    frame = buffer[:3]
                    buffer = buffer[3:]

                    rpm = (frame[2] << 8) | frame[1]  # 小端组合
                    print(f"[串口] 当前转速: {rpm} RPM")
                    r.set("temperature:current", rpm)

                    # 写入txt日志
                    f.write(f"{rpm}\n")
                    f.flush()  # 及时写入磁盘
                else:
                    # 丢弃无效字节
                    buffer.pop(0)

            time.sleep(0.05)


# 主程序入口
if __name__ == "__main__":
    # MQTT配置
    MQTT_BROKER = "192.168.83.228"
    MQTT_PORT = 1883

    # 串口初始化
    send_mode_sequence()

    # 启动串口读取线程
    serial_thread = threading.Thread(target=read_serial_loop, daemon=True)
    serial_thread.start()

    # MQTT初始化
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # 开始循环
    client.loop_forever()
