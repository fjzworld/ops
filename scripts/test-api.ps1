# 运维平台 API 测试脚本 (PowerShell)

$baseUrl = "http://localhost:8000/api/v1"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "运维平台 API 测试" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# 1. 创建管理员账号
Write-Host "1. 创建管理员账号..." -ForegroundColor Yellow
$registerBody = @{
    username = "admin"
    email    = "admin@example.com"
    password = "admin123"
    role     = "admin"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    Write-Host "✓ 管理员账号创建成功: $($response.username)" -ForegroundColor Green
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "⚠ 管理员账号已存在,跳过创建" -ForegroundColor Yellow
    }
    else {
        Write-Host "✗ 创建失败: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# 2. 登录获取 Token
Write-Host "2. 登录获取 Token..." -ForegroundColor Yellow
$loginBody = @{
    username = "admin"
    password = "admin123"
}

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/x-www-form-urlencoded"
    $token = $response.access_token
    Write-Host "✓ 登录成功,Token: $($token.Substring(0, 20))..." -ForegroundColor Green
}
catch {
    Write-Host "✗ 登录失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
}

Write-Host ""

# 3. 获取当前用户信息
Write-Host "3. 获取当前用户信息..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/me" -Method Get -Headers $headers
    Write-Host "✓ 用户: $($response.username), 角色: $($response.role)" -ForegroundColor Green
}
catch {
    Write-Host "✗ 获取用户信息失败" -ForegroundColor Red
}

Write-Host ""

# 4. 创建测试资源
Write-Host "4. 创建测试资源..." -ForegroundColor Yellow
$resourceBody = @{
    name       = "web-server-01"
    type       = "virtual"
    ip_address = "192.168.1.100"
    cpu_cores  = 4
    memory_gb  = 8
    disk_gb    = 100
    os_type    = "Ubuntu 22.04"
} | ConvertTo-Json

$resourceId = $null
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/resources" -Method Post -Body $resourceBody -Headers $headers -ContentType "application/json"
    Write-Host "✓ 资源创建成功: $($response.name) (ID: $($response.id))" -ForegroundColor Green
    $resourceId = $response.id
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "⚠ 资源已存在,获取资源列表..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$baseUrl/resources" -Method Get -Headers $headers
        if ($response.Count -gt 0) {
            $resourceId = $response[0].id
        }
    }
    else {
        Write-Host "✗ 创建资源失败: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# 5. 更新资源指标
if ($resourceId) {
    Write-Host "5. 更新资源指标..." -ForegroundColor Yellow
    $metricsBody = @{
        cpu_usage    = 75.5
        memory_usage = 60.2
        disk_usage   = 45.8
    } | ConvertTo-Json

    try {
        $null = Invoke-RestMethod -Uri "$baseUrl/resources/$resourceId/metrics" -Method Post -Body $metricsBody -Headers $headers -ContentType "application/json"
        Write-Host "✓ 资源指标更新成功" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ 更新指标失败" -ForegroundColor Red
    }
}

Write-Host ""

# 6. 获取资源列表
Write-Host "6. 获取资源列表..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/resources" -Method Get -Headers $headers
    Write-Host "✓ 共有 $($response.Count) 个资源" -ForegroundColor Green
    foreach ($resource in $response) {
        Write-Host "  - $($resource.name): CPU $($resource.cpu_usage)%, 内存 $($resource.memory_usage)%"
    }
}
catch {
    Write-Host "✗ 获取资源列表失败" -ForegroundColor Red
}

Write-Host ""

# 7. 创建告警规则
Write-Host "7. 创建告警规则..." -ForegroundColor Yellow
$ruleBody = @{
    name                  = "CPU 使用率过高"
    metric                = "cpu_usage"
    condition             = ">"
    threshold             = 80
    severity              = "warning"
    notification_channels = @("email")
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/alerts/rules" -Method Post -Body $ruleBody -Headers $headers -ContentType "application/json"
    Write-Host "✓ 告警规则创建成功: $($response.name)" -ForegroundColor Green
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "⚠ 告警规则已存在" -ForegroundColor Yellow
    }
    else {
        Write-Host "✗ 创建告警规则失败" -ForegroundColor Red
    }
}

Write-Host ""

# 8. 获取监控仪表盘数据
Write-Host "8. 获取监控仪表盘数据..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/monitoring/dashboard" -Method Get -Headers $headers
    Write-Host "✓ 仪表盘数据:" -ForegroundColor Green
    Write-Host "  - 总资源数: $($response.total_resources)"
    Write-Host "  - 平均 CPU: $([math]::Round($response.average_cpu_usage, 2))%"
    Write-Host "  - 平均内存: $([math]::Round($response.average_memory_usage, 2))%"
}
catch {
    Write-Host "✗ 获取仪表盘数据失败" -ForegroundColor Red
}

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "测试完成!" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问前端: http://localhost:5173" -ForegroundColor Green
Write-Host "登录账号: admin / admin123" -ForegroundColor Green
