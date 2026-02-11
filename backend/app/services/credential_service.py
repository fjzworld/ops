import logging
from typing import Optional
from app.models.resource import Resource
from app.services.resource_detector import SSHCredentials
from app.core.encryption import decrypt_string
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

class CredentialService:
    @staticmethod
    def build_ssh_credentials(
        ip_address: str, 
        port: int, 
        username: Optional[str], 
        password: Optional[str] = None, 
        private_key: Optional[str] = None
    ) -> SSHCredentials:
        """
        Build SSH credentials object from components.
        """
        return SSHCredentials(
            host=ip_address,
            port=port or 22,
            username=username or "root",
            password=password,
            private_key=private_key
        )

    @classmethod
    def get_ssh_credentials(cls, resource: Resource) -> SSHCredentials:
        """
        Build SSH credentials from resource record.
        Raises BadRequestException if credentials are not available or decryption fails.
        """
        if not resource.ip_address:
            raise BadRequestException(message="资源没有配置 IP 地址")
        
        password = None
        private_key = None
        decryption_failed = False
        
        if resource.ssh_password_enc:
            password = decrypt_string(resource.ssh_password_enc)
            if password is None:
                decryption_failed = True
        
        if resource.ssh_private_key_enc:
            private_key = decrypt_string(resource.ssh_private_key_enc)
            if private_key is None:
                decryption_failed = True
        
        if not password and not private_key:
            if decryption_failed:
                raise BadRequestException(message="SSH 凭据解密失败，请重新添加资源以更新凭据")
            raise BadRequestException(message="资源没有保存 SSH 凭据，无法连接")
        
        return cls.build_ssh_credentials(
            ip_address=resource.ip_address,
            port=resource.ssh_port,
            username=resource.ssh_username,
            password=password,
            private_key=private_key
        )
