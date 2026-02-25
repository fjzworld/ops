export interface Middleware {
    id: number;
    name: string;
    type: string;
    resource_id: number;
    port: number;
    username?: string;
    password_enc?: string;
    service_name?: string;
    log_path?: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface MiddlewareCreate {
    name: string;
    type: string;
    resource_id: number;
    port: number;
    username?: string;
    password_plain?: string;
    service_name?: string;
    log_path?: string;
}

export interface MiddlewareUpdate extends Partial<MiddlewareCreate> {
    status?: string;
}

export interface MiddlewareAction {
    action: 'start' | 'stop' | 'restart';
}

export interface MiddlewareListParams {
    skip?: number;
    limit?: number;
}

export interface MiddlewareVerify {
    resource_id: number;
    type: string;
    port: number;
    username?: string;
    password_plain?: string;
    service_name?: string;
}

export interface MiddlewareVerifyResult {
    success: boolean;
    ssh_ok: boolean;
    port_reachable: boolean;
    service_active: boolean;
    auth_valid: boolean;
    auth_message?: string;
    log_path_found: boolean;
    suggested_log_path?: string;
    suggested_service_name?: string;  // 自动检测到的服务名称
    message: string;
    details: Record<string, any>;
}
