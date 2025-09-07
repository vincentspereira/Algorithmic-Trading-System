#!/usr/bin/env python3
"""
Demonstration script for SecretsManager

This script demonstrates the key functionality of the SecretsManager class,
showing how it validates .env files, credentials, API keys, and database connections.
"""

import sys
import time
from pathlib import Path

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from secrets_manager import SecretsManager, ValidationStatus, SecretType, SecurityLevel


def main():
    """Demonstrate SecretsManager functionality"""
    print("=" * 80)
    print("SECRETS MANAGER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize SecretsManager
    print("\n1. Initializing SecretsManager...")
    secrets_manager = SecretsManager()
    print(f"   Project Root: {secrets_manager.project_root}")
    print(f"   Environment Files: {secrets_manager.env_files}")
    print(f"   API Validation Enabled: {secrets_manager.api_validation_enabled}")
    print(f"   Database Validation Enabled: {secrets_manager.database_validation_enabled}")
    
    # Show loaded environment variables (non-sensitive ones)
    print("\n2. Environment Variables Overview...")
    total_vars = len(secrets_manager.env_vars)
    print(f"   Total Variables Loaded: {total_vars}")
    
    # Show some non-sensitive variables
    non_sensitive_vars = [
        'POSTGRES_HOST', 'POSTGRES_PORT', 'REDIS_HOST', 'REDIS_PORT',
        'DEBUG', 'LOG_LEVEL', 'ENVIRONMENT', 'API_HOST', 'API_PORT'
    ]
    
    print("   Sample Non-Sensitive Variables:")
    for var in non_sensitive_vars:
        value = secrets_manager.get_secret_value(var)
        if value:
            print(f"     {var}: {value}")
    
    # Demonstrate secret classification
    print("\n3. Secret Classification Examples...")
    test_secrets = [
        'POSTGRES_PASSWORD',
        'ALPHA_VANTAGE_API_KEY',
        'SECRET_KEY',
        'DATABASE_URL',
        'CLIENT_SECRET',
        'DEBUG'
    ]
    
    for secret_name in test_secrets:
        secret_type = secrets_manager._classify_secret_type(secret_name)
        security_level = secrets_manager._determine_security_level(secret_name, secret_type)
        is_sensitive = secrets_manager._is_sensitive_secret(secret_name, secret_type)
        is_required = secrets_manager._is_required_secret(secret_name)
        
        print(f"   {secret_name}:")
        print(f"     Type: {secret_type.value}")
        print(f"     Security Level: {security_level.value}")
        print(f"     Sensitive: {is_sensitive}")
        print(f"     Required: {is_required}")
    
    # Validate .env file
    print("\n4. .env File Validation...")
    env_result = secrets_manager.validate_env_file()
    
    print(f"   Overall Status: {env_result.overall_status.value}")
    print(f"   Total Secrets: {env_result.total_secrets}")
    print(f"   Valid: {env_result.valid_secrets}")
    print(f"   Invalid: {env_result.invalid_secrets}")
    print(f"   Missing: {env_result.missing_secrets}")
    print(f"   Warnings: {env_result.warning_secrets}")
    
    if env_result.critical_issues:
        print(f"   🚨 Critical Issues ({len(env_result.critical_issues)}):")
        for issue in env_result.critical_issues[:3]:  # Show first 3
            print(f"     - {issue}")
        if len(env_result.critical_issues) > 3:
            print(f"     ... and {len(env_result.critical_issues) - 3} more")
    
    if env_result.high_issues:
        print(f"   ⚠️ High Priority Issues ({len(env_result.high_issues)}):")
        for issue in env_result.high_issues[:3]:  # Show first 3
            print(f"     - {issue}")
        if len(env_result.high_issues) > 3:
            print(f"     ... and {len(env_result.high_issues) - 3} more")
    
    # Show some secret details (masked)
    print("\n5. Secret Analysis Examples...")
    sample_secrets = ['POSTGRES_PASSWORD', 'ALPHA_VANTAGE_API_KEY', 'SECRET_KEY']
    
    for secret_name in sample_secrets:
        secret_value = secrets_manager.get_secret_value(secret_name)
        if secret_value:
            secret_info = secrets_manager._analyze_secret(secret_name, secret_value)
            print(f"   {secret_name}:")
            print(f"     Masked Value: {secret_info.value}")
            print(f"     Status: {secret_info.validation_status.value}")
            print(f"     Strength Score: {secret_info.strength_score}/100")
            if secret_info.validation_message:
                print(f"     Message: {secret_info.validation_message}")
    
    # Ask user about live validations
    print("\n6. Live Validation Options...")
    print("   The following validations can be performed:")
    print("     - Database connection testing")
    print("     - API key validation (makes actual API calls)")
    
    proceed_db = input("   Test database connections? (y/N): ").lower().strip()
    proceed_api = input("   Test API keys? (y/N): ").lower().strip()
    
    # Configure validation options
    secrets_manager.set_validation_options(
        api_validation=(proceed_api == 'y'),
        database_validation=(proceed_db == 'y')
    )
    
    if proceed_db == 'y':
        print("\n7. Database Connection Validation...")
        db_results = secrets_manager.validate_database_connections()
        
        for db_name, status in db_results.items():
            status_icon = "✅" if status == ValidationStatus.VALID else "❌"
            print(f"   {status_icon} {db_name}: {status.value}")
    
    if proceed_api == 'y':
        print("\n8. API Key Validation...")
        print("   ⚠️ This will make actual API calls and may consume quotas")
        confirm_api = input("   Continue with API validation? (y/N): ").lower().strip()
        
        if confirm_api == 'y':
            print("   Testing API keys (this may take a moment)...")
            api_results = secrets_manager.validate_api_keys()
            
            for api_name, status in api_results.items():
                if status == ValidationStatus.VALID:
                    status_icon = "✅"
                elif status == ValidationStatus.INVALID:
                    status_icon = "❌"
                elif status == ValidationStatus.RATE_LIMITED:
                    status_icon = "⏱️"
                elif status == ValidationStatus.MISSING:
                    status_icon = "❓"
                else:
                    status_icon = "⚠️"
                
                print(f"   {status_icon} {api_name}: {status.value}")
        else:
            print("   API validation skipped")
    
    # Comprehensive validation
    print("\n9. Comprehensive Secrets Validation...")
    comprehensive_result = secrets_manager.comprehensive_secrets_validation()
    
    print(f"   Overall Status: {comprehensive_result.overall_status.value}")
    print(f"   Environment Variables: {comprehensive_result.total_secrets}")
    print(f"   Database Connections: {len(comprehensive_result.database_connections)}")
    print(f"   API Keys Tested: {len(comprehensive_result.api_key_validations)}")
    
    # Generate and show report summary
    print("\n10. Security Report Generation...")
    report = secrets_manager.generate_secrets_report()
    
    print(f"   Report generated successfully!")
    print(f"   Report length: {len(report)} characters")
    
    # Show report summary
    report_lines = report.split('\n')
    summary_start = next((i for i, line in enumerate(report_lines) if "SUMMARY:" in line), 0)
    summary_end = next((i for i, line in enumerate(report_lines[summary_start:]) if line.strip() == ""), len(report_lines))
    
    if summary_start > 0:
        print("   Report Summary:")
        for line in report_lines[summary_start:summary_start + summary_end]:
            if line.strip():
                print(f"   {line}")
    
    # Ask about saving full report
    save_report = input("\n   Save full security report to file? (y/N): ").lower().strip()
    if save_report == 'y':
        report_file = Path("secrets_validation_report.txt")
        report_file.write_text(report)
        print(f"   Report saved to: {report_file.absolute()}")
    
    # Show security recommendations
    print("\n" + "=" * 80)
    print("SECURITY RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = [
        "🔐 Use strong, unique passwords for all services",
        "🔄 Rotate secrets regularly (every 90 days)",
        "🏦 Store production secrets in secure vaults (HashiCorp Vault, AWS Secrets Manager)",
        "🔍 Implement secret scanning in CI/CD pipelines",
        "📝 Monitor logs for accidental secret exposure",
        "🚫 Never commit secrets to version control",
        "🔒 Use environment-specific secrets (dev/staging/prod)",
        "📊 Regularly audit secret usage and access",
        "🛡️ Implement least-privilege access for secrets",
        "⚡ Use short-lived tokens where possible"
    ]
    
    for recommendation in recommendations:
        print(f"  {recommendation}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    print(f"Environment Variables: {comprehensive_result.total_secrets} analyzed")
    print(f"Validation Status: {comprehensive_result.overall_status.value.upper()}")
    
    if comprehensive_result.critical_issues:
        print(f"🚨 Critical Issues: {len(comprehensive_result.critical_issues)}")
    if comprehensive_result.high_issues:
        print(f"⚠️ High Priority Issues: {len(comprehensive_result.high_issues)}")
    
    valid_db = sum(1 for status in comprehensive_result.database_connections.values() if status == ValidationStatus.VALID)
    total_db = len(comprehensive_result.database_connections)
    if total_db > 0:
        print(f"Database Connections: {valid_db}/{total_db} valid")
    
    valid_api = sum(1 for status in comprehensive_result.api_key_validations.values() if status == ValidationStatus.VALID)
    total_api = len(comprehensive_result.api_key_validations)
    if total_api > 0:
        print(f"API Keys: {valid_api}/{total_api} valid")
    
    print("\nSecretsManager demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("  ✅ .env file parsing and validation")
    print("  ✅ Secret classification and security analysis")
    print("  ✅ Password strength validation")
    print("  ✅ API key format validation")
    print("  ✅ Database connection testing")
    print("  ✅ Live API key validation")
    print("  ✅ Comprehensive security reporting")
    print("  ✅ Security recommendations")


if __name__ == "__main__":
    main()