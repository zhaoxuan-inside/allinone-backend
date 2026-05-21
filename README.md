# AllInOne Backend

AllInOne 平台后端服务 - 基于微服务架构设计。

## 技术栈

- **语言**: Python 3.13
- **框架**: FastAPI 0.115.0
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **消息队列**: Kafka
- **API网关**: FastAPI + httpx
- **容器**: Docker & Docker Compose

## 微服务架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (8000)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ User Service│      │ News Service│      │ Tools Service│
│   (8001)    │      │   (8002)    │      │    (8003)   │
└─────────────┘      └─────────────┘      └─────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  AI Service │      │Stocks Service│     │Forum Service│
│   (8004)    │      │   (8005)    │      │    (8006)   │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  PostgreSQL │      │   Redis     │      │    Kafka    │
│    (5432)   │      │   (6379)    │      │   (9092)    │
└─────────────┘      └─────────────┘      └─────────────┘
```

## 项目结构

```
allinone-backend/
├── common/                    # 共享核心库
│   ├── src/common/
│   │   ├── __init__.py
│   │   ├── settings.py       # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   ├── cache.py          # Redis缓存
│   │   ├── kafka.py          # Kafka消息队列
│   │   ├── auth.py           # 认证工具
│   │   └── exceptions.py     # 异常处理
│   └── pyproject.toml
├── services/                 # 微服务目录
│   ├── api-gateway/          # API网关服务
│   ├── user-service/         # 用户服务
│   ├── news-service/         # 资讯服务
│   ├── tools-service/        # 工具服务
│   ├── ai-service/           # AI服务
│   ├── stocks-service/       # 股票服务
│   └── forum-service/        # 论坛服务
├── docker-compose.yml        # Docker配置
└── .env                      # 环境变量
```

## 服务说明

| 服务 | 端口 | 职责 |
|-----|------|------|
| **api-gateway** | 8000 | 统一入口、路由分发、负载均衡 |
| **user-service** | 8001 | 用户注册、登录、认证、个人信息 |
| **news-service** | 8002 | 新闻聚合、分类管理、新闻浏览 |
| **tools-service** | 8003 | 在线工具管理、使用记录统计 |
| **ai-service** | 8004 | AI模型管理、对话会话管理 |
| **stocks-service** | 8005 | 股票数据、策略分享、讨论交流 |
| **forum-service** | 8006 | 板块管理、帖子发布、评论互动 |

## 快速开始

### 启动所有服务

```bash
# 启动所有依赖服务和微服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 手动启动单个服务

```bash
# 进入服务目录
cd services/user-service

# 安装依赖
poetry install

# 启动服务
poetry run uvicorn src.user_service.main:app --host 0.0.0.0 --port 8001
```

### 访问地址

- **API网关**: http://localhost:8000
- **用户服务**: http://localhost:8001
- **资讯服务**: http://localhost:8002
- **工具服务**: http://localhost:8003
- **AI服务**: http://localhost:8004
- **股票服务**: http://localhost:8005
- **论坛服务**: http://localhost:8006

### 健康检查

```bash
curl http://localhost:8000/health
```

## 架构特点

1. **独立部署**: 每个服务独立打包、部署和扩展
2. **服务发现**: 通过Docker网络实现服务间通信
3. **统一网关**: API Gateway提供统一入口
4. **共享库**: common模块提供共享工具和配置
5. **异步通信**: Kafka实现服务间异步消息传递

## 开发指南

### 添加新服务

1. 在 `services/` 目录下创建新服务目录
2. 创建 `pyproject.toml` 配置依赖
3. 创建 `Dockerfile`
4. 更新 `docker-compose.yml`
5. 实现服务代码

### 代码规范

- 使用 Poetry 管理依赖
- 遵循 FastAPI 最佳实践
- 使用 SQLAlchemy 2.0 异步模式
- 统一异常处理

## License

MIT