"""Certificate Management Service

Handles TLS/SSL certificate generation, renewal, and validation
for secure communications across all services.
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import ipaddress
import socket

from config.encryption_config import encryption_settings
from .secrets_manager import secrets_manager

logger = logging.getLogger(__name__)

class CertificateManager:
    """Manages TLS/SSL certificates for the trading system"""
    
    def __init__(self):
        self.cert_dir = Path(encryption_settings.TLS_CERT_PATH).parent
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on certificate directory
        os.chmod(self.cert_dir, 0o700)
    
    def generate_ca_certificate(self, 
                              common_name: str = "ATS Root CA",
                              validity_days: int = None) -> Tuple[bytes, bytes]:
        """Generate a Certificate Authority (CA) certificate"""
        if validity_days is None:
            validity_days = encryption_settings.CERT_VALIDITY_DAYS * 10  # CA valid for 10x longer
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=encryption_settings.CERT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "NY"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "New York"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Algorithmic Trading System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Serialize certificate and private key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def generate_server_certificate(self,
                                  common_name: str,
                                  san_list: List[str] = None,
                                  ca_cert_pem: bytes = None,
                                  ca_key_pem: bytes = None,
                                  validity_days: int = None) -> Tuple[bytes, bytes]:
        """Generate a server certificate signed by CA"""
        if validity_days is None:
            validity_days = encryption_settings.CERT_VALIDITY_DAYS
        
        if san_list is None:
            san_list = ["localhost", "127.0.0.1", "::1"]
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=encryption_settings.CERT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Load CA certificate and key if provided
        if ca_cert_pem and ca_key_pem:
            ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
            ca_key = serialization.load_pem_private_key(
                ca_key_pem, password=None, backend=default_backend()
            )
            issuer = ca_cert.subject
            signing_key = ca_key
        else:
            # Self-signed certificate
            issuer = None
            signing_key = private_key
        
        # Create certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "NY"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "New York"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Algorithmic Trading System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Services"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        if issuer is None:
            issuer = subject
        
        # Build SAN list
        san_names = []
        for name in san_list:
            try:
                # Try to parse as IP address
                ip = ipaddress.ip_address(name)
                san_names.append(x509.IPAddress(ip))
            except ValueError:
                # Not an IP, treat as DNS name
                san_names.append(x509.DNSName(name))
        
        # Create certificate
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName(san_names),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        )
        
        cert = cert_builder.sign(signing_key, hashes.SHA256(), default_backend())
        
        # Serialize certificate and private key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def generate_client_certificate(self,
                                  common_name: str,
                                  ca_cert_pem: bytes,
                                  ca_key_pem: bytes,
                                  validity_days: int = None) -> Tuple[bytes, bytes]:
        """Generate a client certificate for mutual TLS authentication"""
        if validity_days is None:
            validity_days = encryption_settings.CERT_VALIDITY_DAYS
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=encryption_settings.CERT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Load CA certificate and key
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
        ca_key = serialization.load_pem_private_key(
            ca_key_pem, password=None, backend=default_backend()
        )
        
        # Create certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "NY"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "New York"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Algorithmic Trading System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Clients"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_key, hashes.SHA256(), default_backend())
        
        # Serialize certificate and private key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def save_certificate(self, cert_pem: bytes, key_pem: bytes, 
                        cert_name: str, ca_cert_pem: bytes = None) -> Dict[str, str]:
        """Save certificate and key to files"""
        cert_path = self.cert_dir / f"{cert_name}.crt"
        key_path = self.cert_dir / f"{cert_name}.key"
        
        # Save certificate
        with open(cert_path, 'wb') as f:
            f.write(cert_pem)
        os.chmod(cert_path, 0o644)
        
        # Save private key
        with open(key_path, 'wb') as f:
            f.write(key_pem)
        os.chmod(key_path, 0o600)
        
        paths = {
            'cert': str(cert_path),
            'key': str(key_path)
        }
        
        # Save CA certificate if provided
        if ca_cert_pem:
            ca_path = self.cert_dir / f"{cert_name}-ca.crt"
            with open(ca_path, 'wb') as f:
                f.write(ca_cert_pem)
            os.chmod(ca_path, 0o644)
            paths['ca'] = str(ca_path)
        
        return paths
    
    def load_certificate(self, cert_path: str) -> x509.Certificate:
        """Load certificate from file"""
        with open(cert_path, 'rb') as f:
            cert_pem = f.read()
        return x509.load_pem_x509_certificate(cert_pem, default_backend())
    
    def check_certificate_expiry(self, cert_path: str) -> Dict[str, any]:
        """Check certificate expiration status"""
        try:
            cert = self.load_certificate(cert_path)
            now = datetime.utcnow()
            
            expires_at = cert.not_valid_after
            days_until_expiry = (expires_at - now).days
            
            return {
                'valid': now < expires_at,
                'expires_at': expires_at,
                'days_until_expiry': days_until_expiry,
                'needs_renewal': days_until_expiry <= encryption_settings.CERT_RENEWAL_DAYS_BEFORE,
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': str(cert.serial_number)
            }
        except Exception as e:
            logger.error(f"Failed to check certificate expiry: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def setup_default_certificates(self) -> Dict[str, Dict[str, str]]:
        """Set up default certificates for the trading system"""
        certificates = {}
        
        try:
            # Generate CA certificate
            logger.info("Generating CA certificate...")
            ca_cert_pem, ca_key_pem = self.generate_ca_certificate()
            ca_paths = self.save_certificate(ca_cert_pem, ca_key_pem, "ca")
            certificates['ca'] = ca_paths
            
            # Generate server certificates for different services
            services = [
                ('api-server', ['localhost', '127.0.0.1', 'api-server', 'trading-api']),
                ('kafka', ['localhost', '127.0.0.1', 'kafka', 'kafka-broker']),
                ('redis', ['localhost', '127.0.0.1', 'redis', 'redis-server']),
                ('postgres', ['localhost', '127.0.0.1', 'postgres', 'database']),
                ('frontend', ['localhost', '127.0.0.1', 'frontend', 'web-app']),
            ]
            
            for service_name, san_list in services:
                logger.info(f"Generating certificate for {service_name}...")
                cert_pem, key_pem = self.generate_server_certificate(
                    common_name=service_name,
                    san_list=san_list,
                    ca_cert_pem=ca_cert_pem,
                    ca_key_pem=ca_key_pem
                )
                service_paths = self.save_certificate(
                    cert_pem, key_pem, service_name, ca_cert_pem
                )
                certificates[service_name] = service_paths
            
            # Generate client certificates
            clients = ['trading-client', 'admin-client', 'monitoring-client']
            for client_name in clients:
                logger.info(f"Generating client certificate for {client_name}...")
                cert_pem, key_pem = self.generate_client_certificate(
                    common_name=client_name,
                    ca_cert_pem=ca_cert_pem,
                    ca_key_pem=ca_key_pem
                )
                client_paths = self.save_certificate(
                    cert_pem, key_pem, client_name, ca_cert_pem
                )
                certificates[client_name] = client_paths
            
            logger.info("Default certificates generated successfully")
            return certificates
            
        except Exception as e:
            logger.error(f"Failed to setup default certificates: {e}")
            raise
    
    def renew_certificate(self, cert_name: str) -> bool:
        """Renew an existing certificate"""
        try:
            cert_path = self.cert_dir / f"{cert_name}.crt"
            if not cert_path.exists():
                logger.error(f"Certificate {cert_name} not found")
                return False
            
            # Check if renewal is needed
            expiry_info = self.check_certificate_expiry(str(cert_path))
            if not expiry_info.get('needs_renewal', False):
                logger.info(f"Certificate {cert_name} does not need renewal yet")
                return True
            
            # Load CA certificate
            ca_cert_path = self.cert_dir / "ca.crt"
            ca_key_path = self.cert_dir / "ca.key"
            
            if not (ca_cert_path.exists() and ca_key_path.exists()):
                logger.error("CA certificate or key not found")
                return False
            
            with open(ca_cert_path, 'rb') as f:
                ca_cert_pem = f.read()
            with open(ca_key_path, 'rb') as f:
                ca_key_pem = f.read()
            
            # Generate new certificate
            if cert_name.endswith('-client'):
                cert_pem, key_pem = self.generate_client_certificate(
                    common_name=cert_name,
                    ca_cert_pem=ca_cert_pem,
                    ca_key_pem=ca_key_pem
                )
            else:
                cert_pem, key_pem = self.generate_server_certificate(
                    common_name=cert_name,
                    ca_cert_pem=ca_cert_pem,
                    ca_key_pem=ca_key_pem
                )
            
            # Save renewed certificate
            self.save_certificate(cert_pem, key_pem, cert_name, ca_cert_pem)
            logger.info(f"Certificate {cert_name} renewed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to renew certificate {cert_name}: {e}")
            return False
    
    def get_certificate_info(self, cert_name: str) -> Dict[str, any]:
        """Get detailed information about a certificate"""
        cert_path = self.cert_dir / f"{cert_name}.crt"
        if not cert_path.exists():
            return {'error': f'Certificate {cert_name} not found'}
        
        return self.check_certificate_expiry(str(cert_path))
    
    def list_certificates(self) -> List[Dict[str, any]]:
        """List all certificates and their status"""
        certificates = []
        
        for cert_file in self.cert_dir.glob("*.crt"):
            cert_name = cert_file.stem
            if cert_name.endswith('-ca'):
                continue  # Skip CA files
            
            cert_info = self.get_certificate_info(cert_name)
            cert_info['name'] = cert_name
            certificates.append(cert_info)
        
        return certificates

# Global instance
certificate_manager = CertificateManager()