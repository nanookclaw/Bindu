"""Minimal focused tests for ConfigValidator."""

import pytest

from bindu.penguin.config_validator import ConfigValidator


class TestConfigValidator:
    """Test ConfigValidator with strong test cases."""

    def test_validate_and_process_valid_config(self):
        """Test validation and processing of valid config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result is not None
        assert result["name"] == "TestAgent"
        assert result["author"] == "test@example.com"

    def test_validate_missing_required_field_raises(self):
        """Test validation fails when required field is missing."""
        config = {"version": "1.0.0"}

        with pytest.raises(ValueError, match="author"):
            ConfigValidator.validate_and_process(config)

    def test_validate_missing_deployment_url_raises(self):
        """Test validation fails when deployment.url is missing."""
        config = {"author": "test@example.com", "name": "TestAgent", "deployment": {}}

        with pytest.raises(ValueError, match="deployment.url"):
            ConfigValidator.validate_and_process(config)

    def test_defaults_are_applied(self):
        """Test that default values are applied to config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result["kind"] == "agent"
        assert result["num_history_sessions"] == 10
        assert result["debug_mode"] is False


class TestAgentTrustValidation:
    """Tests for agent_trust config field validation (issue #382)."""

    @staticmethod
    def _base_config():
        return {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

    def _config_with_trust(self, trust_value):
        return {**self._base_config(), "agent_trust": trust_value}

    # ------------------------------------------------------------------
    # Valid configs
    # ------------------------------------------------------------------

    def test_valid_agent_trust_minimal(self):
        """agent_trust with required fields only is accepted."""
        config = self._config_with_trust(
            {
                "identity_provider": {"type": "keycloak"},
                "inherited_roles": [],
            }
        )
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["inherited_roles"] == []

    def test_valid_agent_trust_with_allowed_operations(self):
        """agent_trust with valid trust levels in allowed_operations is accepted."""
        config = self._config_with_trust(
            {
                "identity_provider": {"type": "keycloak"},
                "inherited_roles": [],
                "allowed_operations": {
                    "read_data": "viewer",
                    "write_data": "editor",
                    "admin_panel": "admin",
                },
            }
        )
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["allowed_operations"]["read_data"] == "viewer"

    def test_agent_trust_none_is_allowed(self):
        """agent_trust: null in config is accepted (optional field)."""
        config = self._config_with_trust(None)
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"] is None

    def test_agent_trust_absent_is_allowed(self):
        """Omitting agent_trust entirely uses the default (None)."""
        result = ConfigValidator.validate_and_process(self._base_config())
        assert result["agent_trust"] is None

    # ------------------------------------------------------------------
    # Invalid configs
    # ------------------------------------------------------------------

    def test_agent_trust_non_dict_raises(self):
        """agent_trust must be a dictionary, not a string."""
        config = self._config_with_trust("viewer")
        with pytest.raises(ValueError, match=r"agent_trust.*dictionary"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_missing_identity_provider_raises(self):
        """agent_trust without identity_provider raises ValueError."""
        config = self._config_with_trust({"inherited_roles": []})
        with pytest.raises(ValueError, match=r"identity_provider"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_missing_inherited_roles_raises(self):
        """agent_trust without inherited_roles raises ValueError."""
        config = self._config_with_trust(
            {"identity_provider": {"type": "keycloak"}}
        )
        with pytest.raises(ValueError, match=r"inherited_roles"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_invalid_trust_level_raises(self):
        """agent_trust.allowed_operations with unknown trust level raises ValueError."""
        config = self._config_with_trust(
            {
                "identity_provider": {"type": "keycloak"},
                "inherited_roles": [],
                "allowed_operations": {"read_data": "superuser"},  # invalid
            }
        )
        with pytest.raises(ValueError, match=r"superuser"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_allowed_operations_non_dict_raises(self):
        """agent_trust.allowed_operations must be a dict."""
        config = self._config_with_trust(
            {
                "identity_provider": {"type": "keycloak"},
                "inherited_roles": [],
                "allowed_operations": ["viewer", "editor"],  # list, not dict
            }
        )
        with pytest.raises(ValueError, match=r"allowed_operations.*dictionary"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_inherited_roles_non_list_raises(self):
        """agent_trust.inherited_roles must be a list."""
        config = self._config_with_trust(
            {
                "identity_provider": {"type": "keycloak"},
                "inherited_roles": "admin",  # string, not list
            }
        )
        with pytest.raises(ValueError, match=r"inherited_roles.*list"):
            ConfigValidator.validate_and_process(config)
