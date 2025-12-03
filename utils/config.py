"""
Configuration Manager for PhoneTracker CLI

Handles loading, saving, and managing configuration settings stored in YAML format.
Config file location: ~/.phonetracker/config.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Manages application configuration stored in YAML format."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.phonetracker'
        self.config_file = self.config_dir / 'config.yaml'
        self.db_file = self.config_dir / 'history.db'
        self.log_file = self.config_dir / 'phonetracker.log'
        self._ensure_config_exists()
    
    def _ensure_config_exists(self) -> None:
        """Create config directory and default config if not exists."""
        self.config_dir.mkdir(exist_ok=True)
        
        if not self.config_file.exists():
            default_config = self._get_default_config()
            self.save_config(default_config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration settings."""
        return {
            'voip': {
                'provider': 'twilio',
                'account_sid': '',
                'auth_token': '',
                'phone_number': ''
            },
            'location': {
                'method': 'basic',  # basic, carrier, or gps
                'fallback': True,
                'carrier_api_key': ''
            },
            'auth': {
                'require_confirmation': True,
                'log_all_requests': True,
                'allowed_users': []
            },
            'display': {
                'show_map_link': True,
                'color_output': True,
                'verbose': False,
                'ascii_map': False
            },
            'database': {
                'encrypt': False,
                'path': str(self.db_file)
            },
            'rate_limit': {
                'max_per_hour': 10,
                'max_per_day': 50
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                return config if config else self._get_default_config()
        except FileNotFoundError:
            return self._get_default_config()
        except yaml.YAMLError as e:
            raise ConfigError(f"Error parsing config file: {e}")
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to YAML file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except IOError as e:
            raise ConfigError(f"Error saving config file: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the config key (e.g., 'voip.account_sid')
            default: Default value if key not found
            
        Returns:
            The configuration value or default
        """
        config = self.load_config()
        keys = key_path.split('.')
        
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_value(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the config key (e.g., 'voip.account_sid')
            value: Value to set
        """
        config = self.load_config()
        keys = key_path.split('.')
        
        # Navigate to the correct nested dict
        current = config
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        
        # Convert value to appropriate type
        value = self._convert_value(value)
        current[keys[-1]] = value
        self.save_config(config)
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        if isinstance(value, str):
            # Check for boolean
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
            # Check for integer
            try:
                return int(value)
            except ValueError:
                pass
            # Check for float
            try:
                return float(value)
            except ValueError:
                pass
        return value
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        default_config = self._get_default_config()
        self.save_config(default_config)
    
    def is_configured(self) -> bool:
        """Check if essential Twilio credentials are configured."""
        config = self.load_config()
        voip = config.get('voip', {})
        return bool(
            voip.get('account_sid') and 
            voip.get('auth_token') and 
            voip.get('phone_number')
        )
    
    def display(self) -> Dict[str, Any]:
        """Return config for display (with sensitive values masked)."""
        config = self.load_config()
        
        # Mask sensitive values
        if config.get('voip', {}).get('auth_token'):
            config['voip']['auth_token'] = '****' + config['voip']['auth_token'][-4:]
        if config.get('location', {}).get('carrier_api_key'):
            config['location']['carrier_api_key'] = '****' + config['location']['carrier_api_key'][-4:]
        
        return config


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass
