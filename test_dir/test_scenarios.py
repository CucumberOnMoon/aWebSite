"""
Load all BDD feature files and map them to step definition modules.

pytest-bdd 8.x uses the scenarios() function to register feature files.
Step definitions are imported explicitly to ensure their decorators fire.
"""

# Import step modules so @given/@when/@then decorators register as fixtures
from steps import common_steps     # noqa: F401
from steps import auth_steps       # noqa: F401
from steps import post_steps       # noqa: F401
from steps import nav_steps        # noqa: F401
from steps import dashboard_steps  # noqa: F401

from pytest_bdd import scenarios

# Load all feature files
scenarios('features/authentication.feature')
scenarios('features/posts.feature')
scenarios('features/navigation.feature')
scenarios('features/dashboard.feature')
