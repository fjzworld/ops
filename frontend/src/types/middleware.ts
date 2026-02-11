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
