"""
Create sample resources for testing
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.resource import Resource, ResourceType, ResourceStatus
from datetime import datetime
import random


def create_sample_resources():
    db = SessionLocal()
    
    try:
        # Check if resources already exist
        existing = db.query(Resource).count()
        if existing > 0:
            print(f"Database already has {existing} resources. Skipping sample data creation.")
            return
        
        sample_resources = [
            {
                "name": "web-server-01",
                "type": ResourceType.PHYSICAL,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "192.168.1.10",
                "hostname": "web01.example.com",
                "cpu_cores": 8,
                "memory_gb": 32.0,
                "disk_gb": 500.0,
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "description": "Main web server",
                "cpu_usage": 45.5,
                "memory_usage": 62.3,
                "disk_usage": 35.8,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "db-server-01",
                "type": ResourceType.PHYSICAL,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "192.168.1.20",
                "hostname": "db01.example.com",
                "cpu_cores": 16,
                "memory_gb": 64.0,
                "disk_gb": 1000.0,
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "description": "PostgreSQL database server",
                "cpu_usage": 68.2,
                "memory_usage": 78.5,
                "disk_usage": 56.4,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "app-vm-01",
                "type": ResourceType.VIRTUAL,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "192.168.2.10",
                "hostname": "app01.example.com",
                "cpu_cores": 4,
                "memory_gb": 16.0,
                "disk_gb": 200.0,
                "os_type": "CentOS",
                "os_version": "8.5",
                "description": "Application virtual machine",
                "cpu_usage": 23.4,
                "memory_usage": 45.2,
                "disk_usage": 28.6,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "app-vm-02",
                "type": ResourceType.VIRTUAL,
                "status": ResourceStatus.INACTIVE,
                "ip_address": "192.168.2.11",
                "hostname": "app02.example.com",
                "cpu_cores": 4,
                "memory_gb": 16.0,
                "disk_gb": 200.0,
                "os_type": "CentOS",
                "os_version": "8.5",
                "description": "Standby application server",
                "cpu_usage": 5.1,
                "memory_usage": 12.3,
                "disk_usage": 15.2,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "docker-host-01",
                "type": ResourceType.CONTAINER,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "192.168.3.10",
                "hostname": "docker01.example.com",
                "cpu_cores": 8,
                "memory_gb": 32.0,
                "disk_gb": 500.0,
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "description": "Docker container host",
                "cpu_usage": 52.3,
                "memory_usage": 68.9,
                "disk_usage": 42.1,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "k8s-node-01",
                "type": ResourceType.CONTAINER,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "192.168.3.20",
                "hostname": "k8s01.example.com",
                "cpu_cores": 16,
                "memory_gb": 64.0,
                "disk_gb": 1000.0,
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "description": "Kubernetes master node",
                "cpu_usage": 72.5,
                "memory_usage": 82.1,
                "disk_usage": 48.7,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "cloud-instance-01",
                "type": ResourceType.CLOUD,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "10.0.1.10",
                "hostname": "cloud01.aws.example.com",
                "cpu_cores": 4,
                "memory_gb": 8.0,
                "disk_gb": 100.0,
                "os_type": "Amazon Linux",
                "os_version": "2023",
                "description": "AWS EC2 instance",
                "cpu_usage": 34.2,
                "memory_usage": 56.8,
                "disk_usage": 32.4,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "maintenance-server",
                "type": ResourceType.PHYSICAL,
                "status": ResourceStatus.MAINTENANCE,
                "ip_address": "192.168.1.30",
                "hostname": "maint01.example.com",
                "cpu_cores": 8,
                "memory_gb": 32.0,
                "disk_gb": 500.0,
                "os_type": "Ubuntu",
                "os_version": "20.04",
                "description": "Server under maintenance - OS upgrade",
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 65.3,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "offline-backup",
                "type": ResourceType.PHYSICAL,
                "status": ResourceStatus.OFFLINE,
                "ip_address": "192.168.1.40",
                "hostname": "backup01.example.com",
                "cpu_cores": 4,
                "memory_gb": 16.0,
                "disk_gb": 2000.0,
                "os_type": "Ubuntu",
                "os_version": "22.04",
                "description": "Offline backup server",
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 89.2,
                "last_seen": datetime.utcnow()
            },
            {
                "name": "cloud-instance-02",
                "type": ResourceType.CLOUD,
                "status": ResourceStatus.ACTIVE,
                "ip_address": "10.0.1.20",
                "hostname": "cloud02.azure.example.com",
                "cpu_cores": 8,
                "memory_gb": 16.0,
                "disk_gb": 250.0,
                "os_type": "Windows Server",
                "os_version": "2022",
                "description": "Azure VM instance",
                "cpu_usage": 41.8,
                "memory_usage": 63.2,
                "disk_usage": 38.5,
                "last_seen": datetime.utcnow()
            }
        ]
        
        for data in sample_resources:
            resource = Resource(**data)
            db.add(resource)
        
        db.commit()
        print(f"Successfully created {len(sample_resources)} sample resources!")
        
        # Print summary
        print("\nResource Summary:")
        for resource_type in ResourceType:
            count = db.query(Resource).filter(Resource.type == resource_type).count()
            print(f"  {resource_type.value}: {count}")
        
        print("\nStatus Summary:")
        for status in ResourceStatus:
            count = db.query(Resource).filter(Resource.status == status).count()
            print(f"  {status.value}: {count}")
            
    except Exception as e:
        print(f"Error creating sample resources: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_resources()
