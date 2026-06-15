"""
Runner para tests de OnboardingService con Django configurado.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

# Importar y ejecutar tests
from tests.unit.test_onboarding_service_simple import run_all_tests

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
