"""
Pytest fixtures for BDD + Playwright UI testing against the Django site.

Starts a Django dev server per session, provides a Playwright browser and
page scoped to each scenario (via function scope).
"""

import os
import sys
import socket
import subprocess
import time
import signal
import pytest
from playwright.sync_api import sync_playwright

# Ensure the project root is on sys.path so Django imports work
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ── Session-scoped Django dev server ────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server_url():
    """Start the Django dev server on a free port for the whole test session."""
    port = _get_free_port()
    manage_py = os.path.join(ROOT_DIR, 'manage.py')
    venv_python = os.path.join(ROOT_DIR, 'website', 'Scripts', 'python.exe')

    proc = subprocess.Popen(
        [venv_python, manage_py, 'runserver', f'127.0.0.1:{port}', '--noreload'],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f'http://127.0.0.1:{port}'

    # Wait until the server is ready
    max_retries = 30
    for _ in range(max_retries):
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError('Django dev server failed to start')

    yield url

    # Teardown
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── Playwright browser (session-scoped) ─────────────────────────────────────

@pytest.fixture(scope="session")
def browser():
    """Launch a single Chromium instance for the whole session."""
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        yield b


# ── Page fixture (function-scoped — fresh context per test) ──────────────────

@pytest.fixture
def page(browser, live_server_url):
    """Create a fresh browser context + page for each test."""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='en-US',
    )
    pg = context.new_page()
    pg._base_url = live_server_url  # store for helper use
    yield pg
    context.close()


# ── Pytest-BDD pytestbdd_given / when / then are imported in step files ─────
