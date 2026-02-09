import pytest
from unittest.mock import MagicMock, patch
import paramiko
import os
from app.core.ssh import create_secure_client

class TestSSH:
    @patch('paramiko.SSHClient')
    def test_create_secure_client_policy(self, mock_ssh_client):
        """
        Test that create_secure_client sets the policy to RejectPolicy
        and loads system host keys.
        """
        # Setup the mock
        client_instance = MagicMock()
        mock_ssh_client.return_value = client_instance
        
        # Call the function
        client = create_secure_client()
        
        # Verify the client was created
        assert client == client_instance
        
        # Verify RejectPolicy was set
        # We check if set_missing_host_key_policy was called with an instance of RejectPolicy
        args, _ = client_instance.set_missing_host_key_policy.call_args
        assert isinstance(args[0], paramiko.RejectPolicy)
        
        # Verify load_system_host_keys was called
        client_instance.load_system_host_keys.assert_called_once()

    @patch('app.core.ssh.paramiko.SSHClient')
    def test_connection_rejects_unknown(self, mock_ssh_client):
        """
        Verify that we are using a mechanism that would reject unknown hosts.
        Since we are mocking, we are primarily verifying the configuration.
        Real functional test would require a real SSH server.
        """
        client_instance = MagicMock()
        mock_ssh_client.return_value = client_instance
        
        # We manually set the policy on the mock to behave like RejectPolicy if we were to simulate it,
        # but paramiko's policies are classes.
        # The critical part is ensuring create_secure_client *configures* it correctly.
        
        client = create_secure_client()
        
        # Ensure we are NOT using AutoAddPolicy
        # This is a bit redundant with the previous test but good for emphasis
        args, _ = client_instance.set_missing_host_key_policy.call_args
        assert not isinstance(args[0], paramiko.AutoAddPolicy)
        assert isinstance(args[0], paramiko.RejectPolicy)

