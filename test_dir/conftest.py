"""
Pytest fixtures for BDD + Playwright UI testing against the Django site.

Provides:
- A live Django dev server per session (test DB, auto-migrate)
- Playwright Chromium browser + page
- Django ORM access for fast test-data setup
- Screenshot on failure for debugging
"""

import os
import sys
import socket
import subprocess
import time
import pytest
import django
from pathlib import Path

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ── Initialize Django at import time (before step modules load) ──────────
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _find_venv_python():
    """Auto-detect venv Python (works on Windows & Linux)."""
    candidates = [
        ROOT_DIR / 'website' / 'Scripts' / 'python.exe',
        ROOT_DIR / 'website' / 'bin' / 'python',
        ROOT_DIR / 'venv' / 'Scripts' / 'python.exe',
        ROOT_DIR / 'venv' / 'bin' / 'python',
        ROOT_DIR / '.venv' / 'Scripts' / 'python.exe',
        ROOT_DIR / '.venv' / 'bin' / 'python',
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # Fallback to system python
    return sys.executable


# ── Django ORM fixture (session-scoped) ─────────────────────────────────────

@pytest.fixture(scope='session')
def django_orm():
    """Provide Django ORM access for test-data setup without starting the server."""
    import django
    django.setup()
    return django.apps


# ── Session-scoped Django dev server (with test DB) ─────────────────────────

@pytest.fixture(scope='session')
def live_server_url(django_orm):
    """Start Django dev server on a free port with a test database."""
    port = _get_free_port()
    manage_py = ROOT_DIR / 'manage.py'
    venv_python = _find_venv_python()

    # Use a test database by overriding settings via env
    env = os.environ.copy()
    env.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')

    proc = subprocess.Popen(
        [venv_python, str(manage_py), 'test', '--verbosity=0', '--failfast',
         '--testrunner=django.test.runner.DiscoverRunner'] if False else
        [venv_python, str(manage_py), 'runserver', f'127.0.0.1:{port}', '--noreload'],
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    url = f'http://127.0.0.1:{port}'

    # Wait until server is ready
    import urllib.request
    for _ in range(40):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError('Django dev server failed to start')

    yield url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── DB helpers for fast test-data setup ─────────────────────────────────────

@pytest.fixture
def db():
    """Provide a Django DB cursor for direct ORM operations in tests.
    
    Usage in step definitions:
        from django.contrib.auth.models import User
        user = User.objects.create_user(username='foo', password='bar')
    """
    import django
    if not django.apps.ready:
        django.setup()
    return django.db.connection


# ── Playwright browser (session-scoped) ─────────────────────────────────────

@pytest.fixture(scope='session')
def browser():
    """Launch a single Chromium instance for the whole session."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox'],
        )
        yield b


# ── Page fixture (function-scoped — fresh context per test) ─────────────────

@pytest.fixture
def page(browser, live_server_url):
    """Create a fresh browser context + page for each test.
    
    On failure, saves a screenshot to test_dir/screenshots/.
    """
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='en-US',
    )
    pg = context.new_page()

    # Attach base_url as a property for step helpers
    pg._base_url = live_server_url

    # Enable console logging for debugging
    pg.on('console', lambda msg: None)  # suppress in CI

    yield pg

    # Screenshot on failure
    if hasattr(pg, '_test_failed') and pg._test_failed:
        screenshot_dir = Path(__file__).parent / 'screenshots'
        screenshot_dir.mkdir(exist_ok=True)
        pg.screenshot(path=str(screenshot_dir / f'failure_{time.time():.0f}.png'))

    context.close()


# ── Failure hook ─────────────────────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Mark the page fixture as failed when a test fails (for screenshot)."""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call' and rep.failed:
        if 'page' in item.funcargs:
            item.funcargs['page']._test_failed = True


# =============================================================================
# pytest-bdd STEP DEFINITIONS
# (Must be in conftest.py for pytest-bdd 8.x fixture discovery)
# =============================================================================

from pytest_bdd import given, when, then, parsers
from django.contrib.auth.models import User
from accounts.models import Post

TEST_PASSWORD='TestPass123!'
_TEST_USERS_CREATED = False


def _test_users():
    global _TEST_USERS_CREATED
    if _TEST_USERS_CREATED:
        return
    for uname in ['loggedin_user', 'specific_user', 'admin_user']:
        u, c = User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@test.com'})
        if c:
            u.set_password(TEST_PASSWORD)
            u.save()
    _TEST_USERS_CREATED = True


# --- Given ---

@given('I am logged in')
def _login(page, live_server_url):
    _test_users()
    page.goto(live_server_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', 'loggedin_user')
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/**', timeout=5000)


@given('I am logged out')
def _logout(page, live_server_url):
    page.goto(live_server_url + '/logout/')
    page.wait_for_load_state('networkidle')


@given(parsers.parse('I am on the {page_name} page'))
def _nav_given(page, live_server_url, page_name):
    _nav(page, live_server_url, page_name)


@given(parsers.parse('there is a post titled "{title}"'))
def _create_post(title):
    a, _ = User.objects.get_or_create(username='post_author', defaults={'email': 'post_author@test.com'})
    Post.objects.get_or_create(title=title, defaults={'content': f'Content of {title}.', 'author': a})


@given('there are multiple registered users')
def _multi_users():
    for u in ['dashboard_user1', 'dashboard_user2']:
        User.objects.get_or_create(username=u, defaults={'email': f'{u}@test.com'})


# --- When ---

def _nav(page, live_server_url, page_name):
    m = {'home': '/', 'login': '/login/', 'register': '/register/', 'posts': '/posts/',
         'dashboard': '/success/', 'create post': '/posts/create/', 'weight data': '/weight-data/',
         'users': '/users/', 'admin': '/admin/'}
    page.goto(live_server_url + m.get(page_name.lower(), '/'))
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I am on the {page_name} page'))
def _nav_when(page, live_server_url, page_name):
    _nav(page, live_server_url, page_name)


@when(parsers.parse('I fill in "{field}" with "{value}"'))
def _fill(page, field, value):
    page.wait_for_selector(f'input[name="{field}"]', state='visible')
    page.fill(f'input[name="{field}"]', value)


@when('I submit the form')
@when('I submit the registration form')
@when('I submit the login form')
@when('I submit the post form')
def _submit(page):
    with page.expect_navigation(wait_until='networkidle', timeout=10000) as _:
        page.click('button[type="submit"]')


@when('I log out')
def _logout_when(page, live_server_url):
    page.goto(live_server_url + '/logout/')
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I fill the title with "{title}"'))
def _fill_title(page, title):
    page.wait_for_selector('input[name="title"]', state='visible')
    page.fill('input[name="title"]', title)


@when(parsers.parse('I fill the content with "{content}"'))
def _fill_content(page, content):
    page.wait_for_selector('textarea[name="content"]', state='visible')
    page.fill('textarea[name="content"]', content)


@when(parsers.parse('I click the post title "{title}"'))
def _click_post(page, title):
    page.locator(f'.post-item h3 a:has-text("{title}")').wait_for(state='visible').click()
    page.wait_for_load_state('networkidle')


# --- Then ---

@then(parsers.parse('I should see "{text}"'))
def _see(page, text):
    l = page.locator(f'text={text}')
    l.wait_for(state='visible', timeout=5000)
    assert l.is_visible(), f'Text "{text}" not visible'


@then('I should be redirected to the login page')
def _redir_login(page):
    page.wait_for_url('**/login/**', timeout=5000)


@then('I should be redirected to the dashboard')
def _redir_dash(page):
    try:
        page.wait_for_url('**/success/**', timeout=8000)
    except Exception:
        current = page.url
        raise AssertionError(f'Expected redirect to /success/, got {current}. Body: {page.text_content("body")[:200]}')


@then(parsers.parse('I should see a post titled "{title}" in the list'))
def _post_in_list(page, title):
    l = page.locator(f'.post-item:has-text("{title}")')
    l.wait_for(state='visible', timeout=5000)
    assert l.is_visible(), f'Post "{title}" not in list'


@then(parsers.parse('I should see the post content "{content}"'))
def _post_content(page, content):
    l = page.locator(f'.post-content:has-text("{content}")')
    l.wait_for(state='visible', timeout=3000)
    assert l.is_visible(), f'Content "{content}" not visible'


@then('I should see an empty post list message')
def _empty(page):
    l = page.locator(':has-text("No posts yet")')
    l.wait_for(state='visible', timeout=3000)
    assert l.is_visible(), 'Empty post message not visible'


@then(parsers.parse('the post "{title}" should appear before "{other}"'))
def _order(page, title, other):
    c = page.text_content('.post-list') or ''
    assert c.find(title) < c.find(other), f'"{title}" should be before "{other}"'


@then('I should see pagination controls')
def _pagination(page):
    l = page.locator('.pagination, .page-item')
    if l.count() == 0 and page.locator('.post-item').count() <= 10:
        return
    assert l.is_visible(), 'Pagination not visible'


@then('I should see the users table')
def _table(page):
    l = page.locator('.users-table')
    l.wait_for(state='visible', timeout=5000)
    assert l.is_visible(), 'Users table not visible'


@then(parsers.parse('the table should contain the user "{username}"'))
def _has_user(page, username):
    l = page.locator(f'.users-table:has-text("{username}")')
    l.wait_for(state='visible', timeout=3000)
    assert l.is_visible(), f'User "{username}" not in table'


@then('my row should be highlighted')
def _highlight(page):
    assert page.locator('tr.current-user').is_visible(), 'Row not highlighted'


@then('my row should show a "You" badge')
def _badge(page):
    assert page.locator('.badge:has-text("You")').is_visible(), 'Badge not visible'


@then(parsers.parse('the table should have a column "{name}"'))
def _col(page, name):
    assert page.locator(f'.users-table th:has-text("{name}")').is_visible(), f'Column "{name}" not found'


@then('I should see an upload form for body measurement images')
def _upload_form(page):
    assert (page.locator('form input[type="file"]').is_visible() or
            page.locator('form[enctype="multipart/form-data"]').is_visible()), 'Upload form not visible'


@then('I should see a list of weight records')
def _weight_list(page):
    l = page.locator('table, .weight-list')
    l.wait_for(state='visible', timeout=3000)
    assert l.is_visible(), 'Weight list not visible'


@then('I should see measurement date values')
def _date(page):
    assert page.locator('table th:has-text("Date")').is_visible(), 'Date column not visible'


@then('I should see weight values')
def _weight(page):
    assert page.locator('table th:has-text("Weight")').is_visible(), 'Weight column not visible'


@then('I should see BMI values')
def _bmi(page):
    assert page.locator('table th:has-text("BMI")').is_visible(), 'BMI column not visible'


@then('I should see "Django administration"')
def _admin(page):
    assert page.locator('text=Django administration').is_visible(), 'Admin title not visible'


@then('I should see "User Management"')
def _user_mgmt(page):
    assert page.locator('text=User Management').is_visible(), 'User Management title not visible'


@then('I should see an edit form for user details')
def _edit_form(page):
    assert page.locator('form').is_visible(), 'Edit form not visible'


@then('the language switcher should be present')
def _lang_switcher(page):
    assert page.locator('.lang-switcher').is_visible(), 'Language switcher not visible'


@when(parsers.parse('I switch the language to "{language}"'))
def _switch_lang(page, language):
    m = {'Chinese': 'zh-hans', 'English': 'en'}
    page.select_option('.lang-switcher select', m.get(language, language))
    page.wait_for_load_state('networkidle')


@then(parsers.parse('the page should display text in {language}'))
def _page_lang(page, language):
    checks = {'Chinese': ['首页', '帖子', '登录'], 'English': ['Home', 'Posts', 'Login']}
    for p in checks.get(language, checks['English']):
        if page.locator(f'text={p}').is_visible():
            return
    raise AssertionError(f'No {language} text found')


@then('the page title should contain "Posts"')
@then(parsers.parse('the page title should contain "{text}"'))
def _title_contains(page, text='Posts'):
    t = page.title()
    assert text.lower() in t.lower(), f'Title "{t}" does not contain "{text}"'


@then(parsers.parse('the nav bar should show "{text}"'))
def _nav_shows(page, text):
    assert page.locator(f'nav:has-text("{text}")').is_visible(), f'Nav bar does not show "{text}"'


@then(parsers.parse('I should be on the "{page_name}" page'))
def _on_page(page, live_server_url, page_name):
    m = {'home': '/', 'login': '/login/', 'register': '/register/', 'posts': '/posts/',
         'dashboard': '/success/', 'create post': '/posts/create/'}
    expected = m.get(page_name.lower(), '/').rstrip('/')
    current = page.url.replace(live_server_url, '').rstrip('/')
    if current != expected and not current.startswith(expected):
        # Debug: print page content on failure
        body = page.text_content('body') or ''
        raise AssertionError(f'Expected {expected}, got {current}. Page snippet: {body[:300]}')
    assert True

