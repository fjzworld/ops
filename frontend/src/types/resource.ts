export enum ResourceType {
    PHYSICAL = 'PHYSICAL',
    VIRTUAL = 'VIRTUAL',
    CONTAINER = 'CONTAINER',
    CLOUD = 'CLOUD'
}

export enum ResourceStatus {
    ACTIVE = 'ACTIVE',
    INACTIVE = 'INACTIVE',
    MAINTENANCE = 'MAINTENANCE',
    OFFLINE = 'OFFLINE'
}

export interface Resource {
    id: number;
    name: string;
    type: ResourceType;
    status: ResourceStatus;
    ip_address?: string;
    hostname?: string;
    cpu_cores?: number;
    memory_gb?: number;
    disk_gb?: number;
    os_type?: string;
    os_version?: string;
    tags: string[];
    labels: Record<string, string>;
    description?: string;
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    created_at?: string;
    updated_at?: string;
    last_seen?: string;
    has_credentials: boolean;
    ssh_port?: number;
    ssh_username?: string;
}

export interface Metric {
    id: number;
    resource_id: number;
    timestamp: string;
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_in?: number;
    network_out?: number;
}

export interface DiskPartition {
    mountpoint: string;
    device: string;
    percent: number;
    total_gb: number;
    used_gb: number;
}

export interface ResourceMetrics {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    memory_total?: number;
    memory_used?: number;
    disk_total?: number;
    disk_used?: number;
    network_in?: number;
    network_out?: number;
    top_processes?: any[];
}

export interface Alert {
    id: number;
    resource_id: number;
    severity: string;
    message: string;
    status: string;
    fired_at: string;
}

export interface ResourceMetricsUpdate {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    disk_partitions?: DiskPartition[];
    network_in?: number;
    network_out?: number;
    top_processes?: any[];
}

export interface ResourceListParams {
    skip?: number;
    limit?: number;
    resource_type?: ResourceType;
    status?: ResourceStatus;
}

export interface ResourceCreateRequest {
    name: string;
    type: ResourceType;
    ip_address: string;
    ssh_port?: number;
    ssh_username?: string;
    ssh_password?: string;
    ssh_private_key?: string;
    labels?: Record<string, string>;
    description?: string;
    backend_url?: string;
}

export interface ResourceUpdateRequest extends Partial<ResourceCreateRequest> { }

export interface ResourceDeleteRequest {
    uninstall_agent: boolean;
    ssh_port?: number;
    ssh_username?: string;
    ssh_password?: string;
    ssh_private_key?: string;
}
