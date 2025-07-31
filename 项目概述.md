**支持实时温度反馈和设定的局域网温控控制系统**：从用户输入目标温度、后端控制模拟、实时曲线显示、再到数据存储的完整闭环控制流程。

项目目标：

- 实现温度目标值设定与实时反馈显示；
- 构建控制器模拟真实控制行为；
- 支持 Web 页面操作与可视化；
- 全系统运行于局域网，稳定、安全；
- 增强通信效率，支持 WebSocket 推送当前温度。



## 架构设计

整个系统由 5 大容器服务组成，使用 Docker Compose 管理：

```
Docker Compose 项目
├── frontend      (React + WebSocket 前端界面)
├── backend       (Flask + WebSocket API 服务)
├── controller    (控制器，执行闭环控制并写入 Redis + TimescaleDB)
├── redis         (高速共享状态缓存)
├── timescaledb   (温度历史数据持久化)
└── grafana       (可视化，访问 localhost:3000)
```



## 技术栈总结

| 模块       | 技术选型                 | 作用说明                         |
| ---------- | ------------------------ | -------------------------------- |
| 前端       | React + Socket.IO Client | 表单输入、图表展示、实时温度更新 |
| 反向代理   | Nginx                    | 转发 `/api/*` 请求到 Flask 服务  |
| 后端       | Flask + Flask-SocketIO   | 提供 REST 接口和 WebSocket 推送  |
| 控制器     | Python 控制脚本          | 模拟 PID 控制器逻辑、更新温度    |
| 缓存数据库 | Redis                    | 快速读写当前温度、目标值等状态   |
| 时序数据库 | TimescaleDB + PostgreSQL | 存储温度时间序列数据，用于可视化 |
| 可视化     | Grafana                  | 实时监控温度变化趋势             |



## 各模块作用与交互流程

```plaintext
 用户访问前端页面 http://<局域网IP>:80
  └─> React 页面加载 REST 接口 (/api/temperature/setpoint) 获取当前目标温度
  └─> 提交表单时 POST 新目标温度给 Flask 后端
  └─> 同时通过 WebSocket 接收实时温度更新

 Flask Backend
  ├─ REST API：处理设定值的 GET/POST 请求
  └─ WebSocket：每秒通过 Redis 拉取当前温度并推送给前端

 控制器（Controller）
  └─ 从 Redis 中读取目标设定温度
  └─ 执行简单 P 控制计算，生成 current_temp
  └─ 将当前温度写入 Redis（供 Flask 拉取）、写入 TimescaleDB（供 Grafana 展示）

 Grafana
  └─ 查询 TimescaleDB，展示温度历史趋势图表（如1小时、24小时等）
```



## 关键交互协议

- REST 接口：
  - `GET /api/temperature/setpoint`：获取当前目标温度
  - `POST /api/temperature/setpoint`：更新目标温度
- WebSocket：
  - 客户端连接后持续接收 `{ current: 74.3 }` 格式的数据包



## 网络与访问设计

- 所有服务仅在 **局域网内部署**，没有暴露公网服务；
- 前端通过 Docker 容器内的 Nginx 映射至 80 端口；
- 内部容器通过服务名（如 `flask-backend`）互联；
- WebSocket 由前端自动根据当前地址连接（兼容动态 IP）：

```js
const socket = io(); // 自动使用 window.location.host
```



## 工程管理

- 使用 `docker-compose` 启动完整环境；
- 所有配置通过环境变量控制（Redis 地址、DB 账号等）；
- 前端构建使用多阶段 `Dockerfile`；
- 使用 `nginx.conf` 转发 API 请求并支持 SPA 刷新。



## 关键功能

-  前端设定温度并反馈更新状态
-  后端 REST 接口完成温度的读写
-  WebSocket 实时推送当前温度
-  控制器持续闭环控制并写入 Redis、TimescaleDB
-  Grafana 实时可视化曲线
-  所有服务通过局域网自动访问，无需写死 IP



## 改进建议

- 改进控制算法
- Grafana中增加更细致的图像
- 增加 Web 界面温度趋势图（React 中集成图表库）
- 多用户协作支持（如权限、记录不同用户的设定值）
- 使用 JWT 等方式进行 API 鉴权（管理中台）
- 支持外网访问（使用 Traefik + HTTPS）

值得考虑的问题：经常需要要单独更改某个模块的控制方案时，需要去服务器，导致其他模块的正常运行受到影响。解决方法：可采用单站集控网络结构，各自工序使用各自的上位机，运行各自的程序，互不干扰。



## 说明

前端：

`package.json`是前端的核心配置文件，整合了所有的依赖和脚本。其中：

`"dependencies"`列出了所有依赖。特别注意版本控制，是语义化版本控制，如`^18.2.0`是指允许安装18.2.0及以上，但低于19.0.0的版本。

`"scripts"`包含开发与构建脚本，其中`"start"`是启动开发服务器（默认是在http://localhost:3000）；`"build"`是生成生产环境代码，混淆压缩文件并保存在了build目录下。

可以看到，这个文件中设置了代理：`"proxy": "http://localhost:8000"`。这个地址应当是后端的地址，本项目后端flask运行在8000端口，故这样写。在开发模式下（即执行`npm start`或者`yarn  start`），前端请求会自动代理到这个地址，从而解决与后端跨域的问题。但是在生产环境下（即执行`npm run build`或者本项目使用的`yarn build`），这个`"proxy"`设置**不生效**，需要使用Nginx反向代理，将前后端统一到80端口（见前端的`nginx.conf`，代理之后，前端发起的所有非静态资源请求（如`/api/data`）会自动代理到`http://localhost:8000/api/data`），后端flask直接配置CORS。

前端构建：

如果还没安装依赖，首先使用该命令安装`package.json`中指定的所有依赖：

```cmd
yarn install
```

已经安装过依赖以后，要在开发模式下预览，可用：

```cmd
yarn dev
```

准备好之后，请构建生产版本：

```cmd
yarn build
```

这个命令会将React 应用编译、优化并打包到 `build` 或 `dist` 文件夹中，它就是可以部署到服务器上的静态文件。这些yarn的命令是在`package.json`指定的。

注意，容器中已经安排了生产版本的构建，所以在容器中运行前，只要保证依赖已经安装，即已经存在`yarn.lock`文件即可。



### Nginx

**反向代理（Reverse Proxy）** 是 Nginx 的核心功能之一，它的作用类似于一个“中间人”，代表后端服务器处理客户端的请求。与正向代理不同，反向代理的重点是**隐藏和保护后端服务器**。

|              | **正向代理（Forward Proxy）** | **反向代理（Reverse Proxy）**       |
| ------------ | ----------------------------- | ----------------------------------- |
| **使用者**   | 客户端                        | 服务器                              |
| **作用**     | 帮客户端隐藏身份              | 帮后端服务器隐藏身份（如负载均衡）  |
| **典型场景** | 企业内网代理                  | Nginx 转发请求到 Flask/Node.js 后端 |

正向代理就像通过中介租房，反向代理就像房东委托中介处理租客请求（租客不知道真实房东是谁）。

在该系统中，反向代理是这样工作的：

```nginx
location /api/ {
    proxy_pass http://flask-backend:8000;
}
```

- **用户视角**：访问 `http://localhost/api/data`，以为在和 Nginx 直接交互。  
- **实际流程**：  
  1. 用户请求 `http://localhost/api/data` ， Nginx 接收请求。  
  2. Nginx **秘密转发**请求到 `http://flask-backend:8000/api/data`（用户无感知）。  
  3. Flask 处理请求并返回结果 ， Nginx 将结果原样返回给用户。  

采用反向代理，对用户来说，

- **简化访问**：用户只需记住域名（如 `example.com`），无需关心后端服务地址和端口。  
- **提升安全性**：隐藏后端服务器的真实 IP 和端口，防止直接暴露到公网。  

对服务器来说，

- **负载均衡**：可以将请求分发到多个后端服务器（目前的配置是单后端，以后可扩展）。  
- **解耦协议**：Nginx 处理 HTTPS/SSL，后端只需 HTTP（通过 `X-Forwarded-Proto` 告知后端真实协议）。  
- **统一入口**：一个域名下可代理多个服务（如 `/api/` 给 Flask，`/` 给前端静态文件）。  



如果没有反向代理，

```
用户 → 直接访问 Flask 服务（暴露 :8000 端口）
```

需开放 8000 端口到公网，容易被攻击。且无法同时部署前端和后端在同一域名下。  

有反向代理，

```
用户 → Nginx（:80） → 内部转发到 Flask（:8000）  
```

用户只和 Nginx 通信，Flask 藏在内部网络。并且可灵活扩展（如添加缓存、限流、防火墙规则）。  



使用反向代理，理论上会增加一点延迟（多了一次转发），但 Nginx 性能极高，且可以启用缓存优化。  

反向代理是 API 网关的基础功能，API 网关通常还集成鉴权、限流、日志等高级功能。



### websocket支持

```
location /socket.io/ {
        proxy_pass http://flask-backend:8000;   # 代理目标，也就是要把请求转发给谁
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade; # 将客户端的 Upgrade 头（值通常是 websocket）原样传递给后端。
        # WebSocket 握手：客户端发送 Upgrade: websocket 头，表示希望升级到 WebSocket 协议。

        proxy_set_header Connection "upgrade";
        # 关键作用：强制设置 Connection: upgrade 头，告知后端同意协议升级。
        # 与普通 HTTP 的区别：普通请求的 Connection 头通常是 keep-alive 或 close。

        proxy_set_header Host $host; # 保留原始请求的 Host 头（如 localhost），避免后端因域名丢失处理异常。
    }
```

#### **完整握手流程（通过 Nginx 代理）**

1. **客户端 → Nginx**

   ```
   GET /socket.io/ HTTP/1.1
   Host: localhost
   Upgrade: websocket
   Connection: Upgrade
   ```

2. **Nginx → Flask 后端**

   ```
   GET /socket.io/ HTTP/1.1
   Host: localhost
   Upgrade: websocket
   Connection: upgrade  # Nginx 修改了大小写（不影响功能）
   ```

3. **Flask → Nginx → 客户端**

   ```
   HTTP/1.1 101 Switching Protocols
   Upgrade: websocket
   Connection: upgrade
   ```



### 数据库初始化

创建 temperature_data 表。执行：

```sql
CREATE TABLE IF NOT EXISTS temperature_data (
                timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                current_temp DOUBLE PRECISION NOT NULL
            )
```

修改表 temperature_data，将字段（列）current_temp 设置为可以为 NULL。

```sql
ALTER TABLE temperature_data ALTER COLUMN current_temp DROP NOT NULL;
```



### Grafana配置

需要先在Grafana 中配置 TimescaleDB 数据源。

1. 登录 Grafana（看docker-compose中是怎么设定的，默认是http://localhost:3000，默认用户名admin，密码admin）

2. 添加数据源 → 选择 PostgreSQL

- Host: `timescaledb:5432`
- Database: `metrics`
- User: `admin`
- Password: `admin123`
- TLS/SSL Mode设为disable


      3. 保存。

创建新仪表盘，添加图表面板：

示例sql:

```sql
SELECT
  time AS "time",
  temperature AS "value"
FROM sensor_data
ORDER BY time DESC
LIMIT 100
```

另外，在页面上还可以设置刷新间隔、刷新频率等。



### 管理平台

注意信息安全，按照安全性分级管理，以及人员权限设定。

原先，业务人员分析数据需要技术人员的支持。现在通过合理设计平台，降低技术门槛，使业务人员可自主进行分析。

平台包括绩效管理、成本管理、生产制造管理等。

### 关于中台

启动后端框架（SpringBoot项目结构+启动类）

写一个设备注册接口（控制器@RestController+@PostMapping）

定义一个设备模型（Java类+@Getter @Setter）

模拟设备状态管理，/devices接口（Map存设备状态/List存设备，可考虑数据库）

返回设备列表（Get接口）

