"""TLS/SSL Configuration Module

Provides secure TLS/SSL configurations for all services in the trading system.
Handles certificate management, SSL contexts, and secure connection setup.
"""

import ssl
import socket
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

try:
    import OpenSSL
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class TLSConfig:
    """TLS/SSL Configuration Manager"""
    
    # Secure cipher suites (ordered by preference)
    SECURE_CIPHER_SUITES = [
        # TLS 1.3 cipher suites
        'TLS_AES_256_GCM_SHA384',
        'TLS_CHACHA20_POLY1305_SHA256',
        'TLS_AES_128_GCM_SHA256',
        
        # TLS 1.2 cipher suites (ECDHE with PFS)
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-CHACHA20-POLY1305',
        'ECDHE-ECDSA-AES256-GCM-SHA384',
        'ECDHE-ECDSA-AES128-GCM-SHA256',
        'ECDHE-ECDSA-CHACHA20-POLY1305',
    ]
    
    # Weak cipher suites to avoid
    WEAK_CIPHER_SUITES = [
        'RC4', 'DES', '3DES', 'MD5', 'SHA1', 'NULL',
        'EXPORT', 'LOW', 'MEDIUM', 'aNULL', 'eNULL'
    ]
    
    def __init__(self, cert_dir: str = "./certs"):
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)
        
        # Certificate paths
        self.ca_cert_path = self.cert_dir / "ca.crt"
        self.ca_key_path = self.cert_dir / "ca.key"
        self.server_cert_path = self.cert_dir / "server.crt"
        self.server_key_path = self.cert_dir / "server.key"
        self.client_cert_path = self.cert_dir / "client.crt"
        self.client_key_path = self.cert_dir / "client.key"
    
    def create_ssl_context(
        self, 
        purpose: str = 'server',
        verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED,
        check_hostname: bool = True,
        ciphers: Optional[str] = None
    ) -> ssl.SSLContext:
        """Create a secure SSL context with best practices"""
        
        if purpose == 'server':
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(self.server_cert_path), str(self.server_key_path))
        elif purpose == 'client':
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(str(self.ca_cert_path))
            if self.client_cert_path.exists():
                context.load_cert_chain(str(self.client_cert_path), str(self.client_key_path))
        else:
            context = ssl.create_default_context()
        
        # Set minimum and maximum TLS versions
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Configure verification
        context.verify_mode = verify_mode
        context.check_hostname = check_hostname and purpose == 'client'
        
        # Security options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        context.options |= ssl.OP_NO_COMPRESSION
        
        # Set secure cipher suites
        if ciphers:
            context.set_ciphers(ciphers)
        else:
            # Use our secure cipher suite list
            secure_ciphers = ':'.join(self.SECURE_CIPHER_SUITES)
            try:
                context.set_ciphers(secure_ciphers)
            except ssl.SSLError:
                # Fallback to default secure ciphers
                context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def get_database_ssl_config(self, database_type: str = 'postgresql') -> Dict[str, Any]:
        """Get SSL configuration for database connections"""
        
        if database_type.lower() == 'postgresql':
            return {
                'sslmode': 'require',
                'sslcert': str(self.client_cert_path) if self.client_cert_path.exists() else None,
                'sslkey': str(self.client_key_path) if self.client_key_path.exists() else None,
                'sslrootcert': str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
                'sslcrl': None,  # Certificate Revocation List
                'ssl_min_protocol_version': 'TLSv1.2',
                'ssl_max_protocol_version': 'TLSv1.3',
            }
        
        elif database_type.lower() == 'clickhouse':
            return {
                'secure': True,
                'verify': True,
                'ca_certs': str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
                'certfile': str(self.client_cert_path) if self.client_cert_path.exists() else None,
                'keyfile': str(self.client_key_path) if self.client_key_path.exists() else None,
                'ssl_version': ssl.PROTOCOL_TLS_CLIENT,
            }
        
        elif database_type.lower() == 'redis':
            return {
                'ssl': True,
                'ssl_cert_reqs': ssl.CERT_REQUIRED,
                'ssl_ca_certs': str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
                'ssl_certfile': str(self.client_cert_path) if self.client_cert_path.exists() else None,
                'ssl_keyfile': str(self.client_key_path) if self.client_key_path.exists() else None,
                'ssl_check_hostname': False,  # Redis typically uses IP addresses
            }
        
        else:
            raise ValueError(f"Unsupported database type: {database_type}")
    
    def get_kafka_ssl_config(self) -> Dict[str, Any]:
        """Get SSL configuration for Kafka connections"""
        return {
            'security_protocol': 'SSL',
            'ssl_check_hostname': True,
            'ssl_cafile': str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
            'ssl_certfile': str(self.client_cert_path) if self.client_cert_path.exists() else None,
            'ssl_keyfile': str(self.client_key_path) if self.client_key_path.exists() else None,
            'ssl_password': None,  # Key password if encrypted
            'ssl_crlfile': None,   # Certificate Revocation List
        }
    
    def get_http_ssl_config(self, verify_ssl: bool = True) -> Dict[str, Any]:
        """Get SSL configuration for HTTP clients"""
        return {
            'verify': str(self.ca_cert_path) if verify_ssl and self.ca_cert_path.exists() else verify_ssl,
            'cert': (
                str(self.client_cert_path), 
                str(self.client_key_path)
            ) if self.client_cert_path.exists() and self.client_key_path.exists() else None,
            'timeout': 30,
            'ssl_version': ssl.PROTOCOL_TLS_CLIENT,
        }
    
    def get_websocket_ssl_config(self) -> Dict[str, Any]:
        """Get SSL configuration for WebSocket connections"""
        return {
            'ssl': self.create_secure_ssl_context('client'),
            'server_hostname': None,  # Set this based on actual server
        }
    
    def validate_certificate_chain(self, cert_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate certificate chain and return information"""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography library not available for certificate validation")
            return {'valid': False, 'error': 'Cryptography library not available'}
        
        try:
            cert_path = Path(cert_path)
            if not cert_path.exists():
                return {'valid': False, 'error': 'Certificate file not found'}
            
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            # Try to load as PEM first
            try:
                cert = x509.load_pem_x509_certificate(cert_data)
            except ValueError:
                # Try DER format
                cert = x509.load_der_x509_certificate(cert_data)
            
            # Extract certificate information
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            # Check if certificate is expired or will expire soon
            now = datetime.utcnow()
            is_expired = now > not_after
            expires_soon = (not_after - now) < timedelta(days=30)
            
            # Get subject alternative names
            san_list = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                )
                san_list = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass
            
            return {
                'valid': True,
                'subject': subject,
                'issuer': issuer,
                'not_before': not_before,
                'not_after': not_after,
                'is_expired': is_expired,
                'expires_soon': expires_soon,
                'days_until_expiry': (not_after - now).days,
                'subject_alt_names': san_list,
                'serial_number': str(cert.serial_number),
                'version': cert.version.name,
            }
            
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return {'valid': False, 'error': str(e)}
    
    def test_ssl_connection(self, hostname: str, port: int, timeout: int = 10) -> Dict[str, Any]:
        """Test SSL connection to a host and return connection information"""
        try:
            context = self.create_secure_ssl_context('client')
            
            with socket.create_connection((hostname, port), timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # Get connection information
                    cipher = ssock.cipher()
                    cert = ssock.getpeercert()
                    protocol = ssock.version()
                    
                    return {
                        'success': True,
                        'protocol': protocol,
                        'cipher': cipher,
                        'certificate': cert,
                        'hostname': hostname,
                        'port': port,
                    }
                    
        except Exception as e:
            logger.error(f"SSL connection test failed for {hostname}:{port}: {e}")
            return {
                'success': False,
                'error': str(e),
                'hostname': hostname,
                'port': port,
            }
    
    def get_cipher_suite_info(self) -> Dict[str, List[str]]:
        """Get information about available cipher suites"""
        try:
            # Create a temporary context to get available ciphers
            context = ssl.create_default_context()
            
            # Get all available ciphers
            all_ciphers = [cipher['name'] for cipher in context.get_ciphers()]
            
            # Filter secure vs weak ciphers
            secure_ciphers = []
            weak_ciphers = []
            
            for cipher in all_ciphers:
                is_weak = any(weak in cipher.upper() for weak in self.WEAK_CIPHER_SUITES)
                if is_weak:
                    weak_ciphers.append(cipher)
                else:
                    secure_ciphers.append(cipher)
            
            return {
                'all_ciphers': all_ciphers,
                'secure_ciphers': secure_ciphers,
                'weak_ciphers': weak_ciphers,
                'recommended_ciphers': self.SECURE_CIPHER_SUITES,
            }
            
        except Exception as e:
            logger.error(f"Failed to get cipher suite info: {e}")
            return {
                'all_ciphers': [],
                'secure_ciphers': [],
                'weak_ciphers': [],
                'recommended_ciphers': self.SECURE_CIPHER_SUITES,
                'error': str(e),
            }
    
    def create_tls_config_for_service(self, service_name: str) -> Dict[str, Any]:
        """Create TLS configuration for a specific service"""
        
        service_configs = {
            'api_server': {
                'context': self.create_secure_ssl_context('server'),
                'require_client_cert': False,
                'protocols': ['TLSv1.2', 'TLSv1.3'],
            },
            'database': {
                'config': self.get_database_ssl_config('postgresql'),
                'require_ssl': True,
            },
            'redis': {
                'config': self.get_database_ssl_config('redis'),
                'require_ssl': True,
            },
            'kafka': {
                'config': self.get_kafka_ssl_config(),
                'require_ssl': True,
            },
            'http_client': {
                'config': self.get_http_ssl_config(),
                'verify_ssl': True,
            },
            'websocket': {
                'config': self.get_websocket_ssl_config(),
                'require_ssl': True,
            },
        }
        
        if service_name not in service_configs:
            raise ValueError(f"Unknown service: {service_name}")
        
        return service_configs[service_name]
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report"""
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'certificates': {},
            'cipher_suites': self.get_cipher_suite_info(),
            'ssl_tests': {},
            'recommendations': [],
        }
        
        # Check certificates
        cert_files = {
            'ca': self.ca_cert_path,
            'server': self.server_cert_path,
            'client': self.client_cert_path,
        }
        
        for cert_type, cert_path in cert_files.items():
            if cert_path.exists():
                report['certificates'][cert_type] = self.validate_certificate_chain(cert_path)
            else:
                report['certificates'][cert_type] = {
                    'valid': False,
                    'error': 'Certificate file not found'
                }
        
        # Add recommendations based on findings
        recommendations = []
        
        for cert_type, cert_info in report['certificates'].items():
            if not cert_info.get('valid', False):
                recommendations.append(f"Fix {cert_type} certificate: {cert_info.get('error', 'Unknown error')}")
            elif cert_info.get('expires_soon', False):
                recommendations.append(f"Renew {cert_type} certificate (expires in {cert_info.get('days_until_expiry', 0)} days)")
            elif cert_info.get('is_expired', False):
                recommendations.append(f"URGENT: {cert_type} certificate has expired")
        
        if not recommendations:
            recommendations.append("All certificates are valid and not expiring soon")
        
        report['recommendations'] = recommendations
        
        return report

# Global TLS configuration instance
tls_config = TLSConfig()