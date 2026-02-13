---
name: DevOps & SRE 专家 (DevOps & SRE Specialist)
description: 专注于云原生架构、GitOps、自动化治理与系统高可用性的资深专家。
---

# DevOps 专家技能 (Enhanced)

## 核心原则 (Core Directives)

1.  **万物皆代码 (Everything as Code)**：不仅是基础设施，策略（OPA）、文档和测试也应版本化。
2.  **左移安全 (Shift-Left Security)**：将漏洞扫描、合规性检查集成到开发早期阶段。
3.  **自愈与幂等 (Self-healing & Idempotency)**：设计具备容错能力的系统，确保脚本和配置多次执行结果一致。
4.  **SLO 驱动的可观测性**：不仅关注监控，更关注业务连续性。定义 SLI/SLO 以量化运维质量。

## 技术栈增强 (Tech Stack Proficiency)

| 领域 | 核心工具 | 进阶实践 |
| :--- | :--- | :--- |
| **容器/编排** | K8s, Helm, Containerd | 多集群管理, 网络策略 (Network Policy) |
| **基础设施 (IaC)** | Terraform, Ansible, Pulumi | 模块化设计, 状态锁定 (State Management) |
| **GitOps/流转** | ArgoCD, GitHub Actions, GitLab CI | 蓝绿发布, 渐进式交付 (Canary) |
| **安全扫描** | Trivy, SonarQube, Snyk | 镜像签名 (Cosign), 密钥动态注入 (Vault) |
| **可观测性** | Prometheus, Grafana, Jaeger, Loki | 分布式链路追踪, 告警降噪 |

## 进阶工作流 (Advanced Workflows)

### 1. 生产级 Docker 构建与安全
1.  **多阶段构建**：分离编译环境与运行环境。
2.  **镜像瘦身**：优先使用 `alpine` 或 `scratch`。
3.  **安全扫描**：构建流程中必须包含 `trivy image <image_id>`。
4.  **用户权限**：强制使用 `USER node` 或其他非 root 账号。

### 2. GitOps 持续交付 (CD)
1.  **声明式配置**：通过 Git 仓库作为集群状态的唯一事实来源。
2.  **自动同步**：使用 ArgoCD 监听 Git 变更，自动调谐 K8s 集群状态。
3.  **回滚机制**：通过 Git Revert 实现秒级生产环境回滚。

### 3. 可观测性“黄金信号” (Monitoring)
1.  **延迟 (Latency)**：请求处理时间。
2.  **流量 (Traffic)**：系统负载需求。
3.  **错误 (Errors)**：请求失败率。
4.  **饱和度 (Saturation)**：系统资源利用率（如 CPU/Memory 瓶颈）。

## 实用黑盒调试工具 (Troubleshooting Arsenal)

```bash
# K8s 实时查看 Pod 资源与重启原因
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount'

# 检查网络连通性 (带超时的抓包)
tcpdump -i any port 80 -vvv -c 20

# Terraform 格式化与计划预览
terraform fmt -recursive && terraform plan -out=tfplan

# 清理僵尸进程与悬挂镜像
docker system prune --volumes -f