import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import redis
import os
import psycopg2

app = Flask(__name__)
CORS(app, origins="*")  # 从安全性方面考虑，这现在完全开放的，以后可以锁定域名，origins=["http://..."]
socketio = SocketIO(app, cors_allowed_origins="*")  # 创建 SocketIO 实例

# Redis 连接
r = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# PostgreSQL 连接
conn = psycopg2.connect(
    host=os.environ.get("PG_HOST", "timescaledb"),
    port=5432,
    dbname=os.environ.get("PG_DB", "metrics"),
    user=os.environ.get("PG_USER", "admin"),
    password=os.environ.get("PG_PASSWORD", "admin123")
)


@app.route("/api/temperature/setpoint", methods=["GET", "POST"])
def setpoint():
    if request.method == "POST":
        data = request.json
        new_setpoint = data.get("setpoint")
        if new_setpoint is not None:
            r.set("temperature:setpoint", new_setpoint)
            # 广播新设定值给所有连接的客户端
            socketio.emit("setpoint_update", {"value": float(new_setpoint)})
            return jsonify({"status": "success", "setpoint": float(new_setpoint)})
        return jsonify({"error": "Missing value"}), 400
    else:
        value = r.get("temperature:setpoint") or "70"
        return jsonify({"setpoint": float(value)})


@app.route("/api/temperature/current", methods=["GET"])
def current_temperature():
    cur = conn.cursor()
    cur.execute("SELECT current_temp FROM temperature_data ORDER BY timestamp DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    return jsonify({"current_temp": row[0] if row else None})


# PID参数设置接口
@app.route("/api/controller/params", methods=["GET", "POST"])
def controller_params():
    if request.method == "POST":
        data = request.json
        kp = data.get("Kp")
        ki = data.get("Ki")
        kd = data.get("Kd")
        if kp is not None:
            r.set("controller:Kp", kp)
        if ki is not None:
            r.set("controller:Ki", ki)
        if kd is not None:
            r.set("controller:Kd", kd)
        # 广播更新给前端
        socketio.emit("controller_params_update", {
            "Kp": float(kp) if kp is not None else None,
            "Ki": float(ki) if ki is not None else None,
            "Kd": float(kd) if kd is not None else None
        })
        return jsonify({"status": "success", "Kp": kp, "Ki": ki, "Kd": kd})

    else:
        kp = r.get("controller:Kp") or 1.0
        ki = r.get("controller:Ki") or 0.1
        kd = r.get("controller:Kd") or 0.0
        return jsonify({
            "Kp": float(kp),
            "Ki": float(ki),
            "Kd": float(kd)
        })


@app.route("/api/controller/start", methods=["POST"])
def controller_start():
    r.set("controller:enabled", 1)
    socketio.emit("controller_status_update", {"status": "started"})
    return jsonify({"status": "success", "message": "控制器已启动"})


@app.route("/api/controller/stop", methods=["POST"])
def controller_stop():
    r.set("controller:enabled", 0)
    socketio.emit("controller_status_update", {"status": "stopped"})
    return jsonify({"status": "success", "message": "控制器已停止"})


@app.route("/api/controller/status", methods=["GET"])
def controller_status():
    status = r.get("controller:enabled")
    return jsonify({"status": "started" if status == "1" else "stopped"})


def push_current_temperature():
    while True:
        try:
            cur = conn.cursor()
            cur.execute("SELECT current_temp FROM temperature_data ORDER BY timestamp DESC LIMIT 1")
            row = cur.fetchone()
            cur.close()
            if row:
                socketio.emit("current_temp_update", {"value": row[0]})
        except Exception as e:
            print("推送当前速度失败:", e)
        time.sleep(1)


if __name__ == "__main__":
    # 启动推送线程，设置为守护线程，不阻塞主线程
    threading.Thread(target=push_current_temperature, daemon=True).start()
    # 使用 socketio 启动服务器
    socketio.run(app, host="0.0.0.0", port=8000)
