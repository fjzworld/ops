import pytest
import os
from unittest.mock import MagicMock, patch, call
from app.services.alloy_deployer import deploy_alloy_agent
from app.services.resource_detector import SSHCredentials

@pytest.fixture
def mock_ssh_client():
    with patch("app.services.alloy_deployer.create_secure_client") as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Default behavior for exec_command
        def side_effect(cmd, *args, **kwargs):
            mock_stdout = MagicMock()
            mock_stdout.channel.recv_exit_status.return_value = 0
            if "uname -m" in cmd:
                mock_stdout.read.return_value = b"x86_64\n"
            elif "is-active" in cmd:
                mock_stdout.read.return_value = b"active\n"
            else:
                mock_stdout.read.return_value = b"OK\n"
            
            mock_stderr = MagicMock()
            mock_stderr.read.return_value = b""
            return (MagicMock(), mock_stdout, mock_stderr)
            
        client.exec_command.side_effect = side_effect
        
        # Mock SFTP
        mock_sftp = MagicMock()
        client.open_sftp.return_value.__enter__.return_value = mock_sftp
        
        yield client

@patch("os.path.exists")
def test_deploy_alloy_agent_offline_success(mock_exists, mock_ssh_client):
    mock_exists.return_value = True
    
    credentials = SSHCredentials(
        host="1.2.3.4",
        username="testuser",
        password="testpassword"
    )
    
    with patch("builtins.open", MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "fake template content {{ backend_url }}"
        result = deploy_alloy_agent(
            credentials=credentials,
            resource_id=123,
            backend_url="http://backend:8000"
        )
    
    assert result is True
    
    # Check commands
    executed_commands = [c[0][0] for c in mock_ssh_client.exec_command.call_args_list]
    
    # 1. Detect Arch
    assert any("uname -m" in cmd for cmd in executed_commands)
    
    # 2. Upload (mocked sftp.put)
    mock_sftp = mock_ssh_client.open_sftp.return_value.__enter__.return_value
    mock_sftp.put.assert_called_once()
    
    # 3. Install
    assert any("unzip -o /tmp/alloy.zip -d /tmp/alloy_extract" in cmd for cmd in executed_commands)
    assert any("mv /tmp/alloy_extract/alloy-linux-amd64 /usr/local/bin/alloy" in cmd for cmd in executed_commands)
    assert any("chmod +x /usr/local/bin/alloy" in cmd for cmd in executed_commands)
    
    # 4. Configure & Service
    assert any("systemctl daemon-reload" in cmd for cmd in executed_commands)
    assert any("systemctl enable --now alloy" in cmd for cmd in executed_commands)
    
    # 5. Cleanup
    assert any("rm -rf /tmp/alloy.zip /tmp/alloy_extract" in cmd for cmd in executed_commands)

@patch("os.path.exists")
def test_deploy_alloy_agent_missing_binary(mock_exists, mock_ssh_client):
    mock_exists.return_value = False
    
    credentials = SSHCredentials(
        host="1.2.3.4",
        username="testuser",
        password="testpassword"
    )
    
    with pytest.raises(FileNotFoundError) as excinfo:
        deploy_alloy_agent(
            credentials=credentials,
            resource_id=123,
            backend_url="http://backend:8000"
        )
    
    assert "Please download Alloy binary" in str(excinfo.value)
