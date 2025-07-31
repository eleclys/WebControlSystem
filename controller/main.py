# controller/main.py
"""
修改意见：
1. 可以用Redis，但要使用publish-subscribe模式；
2. 用C++重写，保证性能；
"""
import os
import time
import redis
import psycopg2
from datetime import datetime
import paho.mqtt.client as mqtt

# Redis 连接
r = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# PostgreSQL / TimescaleDB 连接
conn = psycopg2.connect(
    host=os.environ.get("PG_HOST", "timescaledb"),
    port=5432,
    dbname=os.environ.get("PG_DB", "metrics"),
    user=os.environ.get("PG_USER", "admin"),
    password=os.environ.get("PG_PASSWORD", "admin123")
)
cur = conn.cursor()

# 请先检查数据库表是否正常

# MQTT配置
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mqtt")  # 替换为公网IP或容器内服务名
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = "control/u"
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()  # 非阻塞后台线程运行

# 控制器参数（PID）
Kp = float(r.get("controller:Kp") or 0.29)
Ki = float(r.get("controller:Ki") or 0.056)
Kd = float(r.get("controller:Kd") or 0.0)
errSum = 0.0
errLast = 0.0

T_history = [0.0]  # 初始速度
targetLast = T_history[-1]  # 初始化为初始速度
T_current = T_history[-1]  # 初始化为初始速度
u = 0  # u初始化为0
print("控制器设定完成，启动中...")

while True:
    try:
        # enabled = r.get("controller:enabled")
        # if enabled != "1":
        #     time.sleep(0.05)
        #     continue

        T_val = r.get("temperature:current")
        if T_val is None:
            print("警告：没有读取到反馈值，跳过当前循环")
            time.sleep(0.05)
            continue
        T_current = float(T_val)

        # 获取目标设定值（默认 140）
        target = float(r.get("temperature:setpoint") or 140)
        err = target - T_current
        errSum += err
        # 积分限幅，防止积分项失控
        errSum = max(min(errSum, 300), -300)
        # u = Kp * err + Ki * errSum + Kd * (err - errLast)  # PID控制器
        errLast = err
        r.set("controller:u", f"{u:.2f}")

        try:
            u = float(r.get("temperature:setpoint") or 140) # 这还是占空比

        except (TypeError, ValueError) as e:
            print("控制量错误：", e)
            print("将按照PWM 140.0运行")

        # 输出限幅（u 作为 PWM 控制量应在 0 ~ 255 范围内）
        u_output = max(min(int(u), 255), 0)

        print(f"PID输出的u: {u:.2f}, 实际输出PWM的u:{u_output:.2f}")

        # MQTT发送控制量
        # client.publish("control/u", f"{pwm:03d}")
        client.publish(MQTT_TOPIC, payload=f"{u_output:03d}")

        r.set("temperature:u", f"{u_output:03d}")  # 保证是3位字符串，因为串口通信用这个量

        # 写入 TimescaleDB
        try:
            cur.execute("INSERT INTO temperature_data (timestamp, current_temp) VALUES (%s, %s)",
                        (datetime.utcnow(), T_current))
            conn.commit()
        except Exception as e:
            print("数据库写入错误:", e)
            conn.rollback()  # 回滚，恢复连接正常状态

        # print(f"目标值: {target:.2f}")
        print(f"[{datetime.now().isoformat()}] 当前速度: {T_current:.2f}")

        time.sleep(0.05)  # 每 0.05 秒更新一次u

    except Exception as e:
        print("控制器错误：", e)
        errSum = 0.0
        errLast = 0.0
        time.sleep(0.05)
