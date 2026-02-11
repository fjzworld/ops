import pytest
from unittest.mock import MagicMock, patch
from app.services.credential_service import CredentialService
from app.core.exceptions import BadRequestException
from app.models.resource import Resource, ResourceType, ResourceStatus
from app.services.resource_detector import SSHCredentials

@patch("app.services.credential_service.decrypt_string")
def test_get_ssh_credentials_success(mock_decrypt):
    mock_decrypt.side_effect = ["decrypted_password", "decrypted_key"]
    
    resource = Resource(
        id=1,
        name="test",
        type=ResourceType.PHYSICAL,
        status=ResourceStatus.ACTIVE,
        ip_address="1.2.3.4",
        ssh_port=22,
        ssh_username="user",
        ssh_password_enc="enc_pass",
        ssh_private_key_enc="enc_key"
    )
    
    creds = CredentialService.get_ssh_credentials(resource)
    
    assert creds.host == "1.2.3.4"
    assert creds.port == 22
    assert creds.username == "user"
    assert creds.password == "decrypted_password"
    assert creds.private_key == "decrypted_key"
    assert mock_decrypt.call_count == 2

def test_get_ssh_credentials_no_ip():
    resource = Resource(ip_address=None)
    with pytest.raises(BadRequestException, match="资源没有配置 IP 地址"):
        CredentialService.get_ssh_credentials(resource)

@patch("app.services.credential_service.decrypt_string")
def test_get_ssh_credentials_decryption_fail(mock_decrypt):
    mock_decrypt.return_value = None
    
    resource = Resource(
        ip_address="1.2.3.4",
        ssh_password_enc="enc_pass"
    )
    
    with pytest.raises(BadRequestException, match="SSH 凭据解密失败"):
        CredentialService.get_ssh_credentials(resource)

def test_get_ssh_credentials_no_creds():
    resource = Resource(
        ip_address="1.2.3.4",
        ssh_password_enc=None,
        ssh_private_key_enc=None
    )
    
    with pytest.raises(BadRequestException, match="资源没有保存 SSH 凭据"):
        CredentialService.get_ssh_credentials(resource)

def test_build_ssh_credentials():
    creds = CredentialService.build_ssh_credentials(
        ip_address="1.2.3.4",
        port=2222,
        username="admin",
        password="password"
    )
    
    assert creds.host == "1.2.3.4"
    assert creds.port == 2222
    assert creds.username == "admin"
    assert creds.password == "password"
    assert creds.private_key is None
