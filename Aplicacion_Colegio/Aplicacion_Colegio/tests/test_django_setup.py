"""
Test simple para verificar configuración de Django
"""
import os
import sys
import django
from django.conf import settings
from django.test import TestCase

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.apps.core.settings')

# Setup Django
if not settings.configured:
    django.setup()

# Import after Django setup - moved inside test method
# from backend.apps.accounts.models import User

class TestDjangoSetup(TestCase):
    """Test simple para verificar que Django está configurado correctamente"""

    def test_django_import(self):
        """Verifica que podemos importar modelos de Django"""
        from backend.apps.accounts.models import User
        self.assertIsNotNone(User)
        print("✓ Django configurado correctamente")