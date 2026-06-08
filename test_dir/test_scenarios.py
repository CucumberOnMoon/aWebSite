"""
Load all BDD feature files.

Step definitions are loaded via steps/conftest.py (pytest-bdd 8.x requires
step fixtures to be in conftest.py for proper discovery).
"""

from pytest_bdd import scenarios

scenarios('features/authentication.feature')
scenarios('features/posts.feature')
scenarios('features/navigation.feature')
scenarios('features/dashboard.feature')
scenarios('features/weight-data.feature')
scenarios('features/admin.feature')
