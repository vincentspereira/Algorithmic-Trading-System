# Test configuration
test_config = {
    'services': {
        'api': {
            'url': 'http://api:8000',
            'endpoints': {
                'health': '/health',
                'dependencies': '/dependencies',
                'validate': '/validate',
                'update': '/update'
            }
        },
        'notification': {
            'url': 'http://notification:8001',
            'endpoints': {
                'health': '/health',
                'send': '/send',
                'templates': '/templates'
            }
        },
        'security': {
            'url': 'http://security:8002',
            'endpoints': {
                'health': '/health',
                'scan': '/scan',
                'vulnerabilities': '/vulnerabilities'
            }
        },
        'dashboard': {
            'url': 'http://dashboard:3000',
            'endpoints': {
                'health': '/api/health',
                'status': '/api/status'
            }
        }
    },
    'test_data': {
        'dependencies': {
            'valid': {
                'name': 'test-dependency',
                'version': '1.0.0',
                'tier': 1,
                'repository': 'org/test-repo',
                'update_frequency': 'weekly'
            },
            'invalid': {
                'name': 'invalid-dep',
                'version': 'bad-version',
                'tier': 'not-a-number'
            }
        },
        'notifications': {
            'channels': ['slack', 'email', 'teams'],
            'templates': {
                'update': 'Update available for {dependency}',
                'security': 'Security vulnerability found in {dependency}'
            }
        },
        'security': {
            'severity_levels': ['critical', 'high', 'medium', 'low'],
            'mock_cve': 'CVE-2023-12345'
        }
    },
    'timeouts': {
        'service_start': 30,
        'api_call': 5,
        'integration_test': 60
    }
}
