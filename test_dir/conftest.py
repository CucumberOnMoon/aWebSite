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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
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

# ── Session-scoped Django dev server (with test DB) ─────────────────────────

@pytest.fixture(scope='session')
def live_server_url():
    """Start Django dev server on a free port with a test database."""
    port = _get_free_port()
    manage_py = ROOT_DIR / 'manage.py'
    venv_python = _find_venv_python()

    # Use a separate test database
    env = os.environ.copy()
    env.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
    test_db = ROOT_DIR / 'test_db.sqlite3'
    env['DJANGO_DATABASE_PATH'] = str(test_db)

    # Create and migrate test database before starting server
    import subprocess as _sp
    if test_db.exists():
        test_db.unlink()
    _sp.run(
        [venv_python, str(manage_py), 'migrate', '--run-syncdb'],
        cwd=str(ROOT_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    proc = subprocess.Popen(
        [venv_python, str(manage_py), 'runserver', f'127.0.0.1:{port}', '--noreload'],
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    url = f'http://127.0.0.1:{port}'

    try:
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
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        try:
            (ROOT_DIR / 'test_db.sqlite3').unlink(missing_ok=True)
        except Exception:
            pass

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


# ── Step definitions (imported from steps/conftest) ──────────────────────

# Imports needed by step definitions
import re
from pytest_bdd import given, when, then, step, parsers
from django.contrib.auth.models import User
from accounts.models import Post
# Test user helpers for BDD steps
TEST_PASSWORD = 'TestPass123!'
TEST_USERS_CREATED = False


def _ensure_test_users():
    global TEST_USERS_CREATED
    if TEST_USERS_CREATED:
        return
    for username in ['loggedin_user', 'specific_user', 'admin_user']:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@test.com'},
        )
        if created:
            user.set_password(TEST_PASSWORD)
            user.save()
    TEST_USERS_CREATED = True





# Given I am logged in
@given('I am logged in')
def _logged_in(page, live_server_url):
    _ensure_test_users()
    page.goto(live_server_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', 'loggedin_user')
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/**', timeout=5000)


# Given I am logged out
@given('I am logged out')

# When I log out
@when('I log out')
def _logged_out(page, live_server_url):
    page.goto(live_server_url + '/logout/')
    page.wait_for_load_state('networkidle')


# When I log in as 
@when(parsers.parse('I log in as "{username}" with password "{password}"'))
def _login_as(page, live_server_url, username, password):
    page.goto(live_server_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# Given I am on the home page
@given('I am on the home page')

# Given I am on the {page_name} page
@given(parsers.parse('I am on the {page_name} page'))

# When I am on the {page_name} page
@when(parsers.parse('I am on the {page_name} page'))
def _navigate(page, live_server_url, page_name='home'):
    PAGE_MAP = {
        'home': '/', 'login': '/login/', 'register': '/register/',
        'posts': '/posts/', 'dashboard': '/success/', 'create post': '/posts/create/',
        'weight data': '/weight-data/', 'users': '/users/', 'admin': '/admin/',
    }
    url = PAGE_MAP.get(page_name.lower(), '/')
    page.goto(live_server_url + url)
    page.wait_for_load_state('networkidle')


# Given I fill in 
@given(parsers.parse('I fill in "{field}" with "{value}"'))

# When I fill in 
@when(parsers.parse('I fill in "{field}" with "{value}"'))
def _fill(page, field, value):
    page.wait_for_selector(f'input[name="{field}"]', state='visible')
    page.fill(f'input[name="{field}"]', value)


# When I submit the form
@when('I submit the form')

# When I submit the registration form
@when('I submit the registration form')

# When I submit the login form
@when('I submit the login form')
def _submit(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# =============================================================================
# COMMON / ASSERTIONS
# =============================================================================

# Then I should see 
@then(parsers.parse('I should see "{text}"'))
def _see_text(page, text):
    loc = page.locator(f'text={text}')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), f'Text "{text}" not visible'


# Then I should be redirected to the login page
@then('I should be redirected to the login page')
def _redirect_login(page):
    page.wait_for_url('**/login/**', timeout=5000)


# Then I should be redirected to the dashboard
@then('I should be redirected to the dashboard')
def _redirect_dash(page):
    page.wait_for_url('**/success/**', timeout=5000)


# Then I should be on the 
@then(parsers.parse('I should be on the "{page_name}" page'))
def _on_page(page, live_server_url, page_name):
    PAGE_MAP = {
        'home': '/', 'login': '/login/', 'register': '/register/',
        'posts': '/posts/', 'dashboard': '/success/', 'create post': '/posts/create/',
    }
    expected = PAGE_MAP.get(page_name.lower(), '/').rstrip('/')
    current = page.url.replace(live_server_url, '').rstrip('/')
    assert current == expected or current.startswith(expected), f'Expected {expected}, got {current}'


# Then the page title should contain 
@then('the page title should contain "Posts"')

# Then the page title should contain 
@then(parsers.parse('the page title should contain "{text}"'))
def _title_contains(page, text='Posts'):
    title = page.title()
    assert text.lower() in title.lower(), f'Title "{title}" does not contain "{text}"'


# Then the nav bar should show 
@then(parsers.parse('the nav bar should show "{text}"'))

# Then the nav bar should display 
@then(parsers.parse('the nav bar should display "{text}"'))
def _nav_shows(page, text):
    assert page.locator(f'nav:has-text("{text}")').is_visible(), f'Nav bar does not show "{text}"'


# =============================================================================
# POST STEPS
# =============================================================================

# Given there is a post titled 
@given(parsers.parse('there is a post titled "{title}"'))
def _create_post(title):
    author, _ = User.objects.get_or_create(username='post_author', defaults={'email': 'post_author@test.com'})
    Post.objects.get_or_create(title=title, defaults={'content': f'Content of {title}.', 'author': author})


# When I fill the title with 
@when(parsers.parse('I fill the title with "{title}"'))
def _fill_title(page, title):
    page.wait_for_selector('input[name="title"]', state='visible')
    page.fill('input[name="title"]', title)


# When I fill the content with 
@when(parsers.parse('I fill the content with "{content}"'))
def _fill_content(page, content):
    page.wait_for_selector('textarea[name="content"]', state='visible')
    page.fill('textarea[name="content"]', content)


# When I submit the post form
@when('I submit the post form')
def _submit_post(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# When I click the post title 
@when(parsers.parse('I click the post title "{title}"'))
def _click_post(page, title):
    link = page.locator(f'.post-item h3 a:has-text("{title}")')
    link.wait_for(state='visible')
    link.click()
    page.wait_for_load_state('networkidle')


# Then I should see a post titled 
@then(parsers.parse('I should see a post titled "{title}" in the list'))
def _post_in_list(page, title):
    loc = page.locator(f'.post-item:has-text("{title}")')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), f'Post "{title}" not in list'


# Then I should see the post content 
@then(parsers.parse('I should see the post content "{content}"'))
def _post_content(page, content):
    loc = page.locator(f'.post-content:has-text("{content}")')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), f'Content "{content}" not visible'


# Then I should see an empty post list message
@then('I should see an empty post list message')
def _empty_list(page):
    loc = page.locator('.empty-row')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), 'Empty post message not visible'


# Then the post 
@then(parsers.parse('the post "{title}" should appear before "{other}"'))
def _post_order(page, title, other):
    """Check post ordering by DOM position, not string search."""
    items = page.locator('.post-item')
    titles = items.all_text_contents()
    pos_title = next((i for i, t in enumerate(titles) if title in t), -1)
    pos_other = next((i for i, t in enumerate(titles) if other in t), -1)
    assert pos_title >= 0, f'Post "{title}" not found in list'
    assert pos_other >= 0, f'Post "{other}" not found in list'
    assert pos_title < pos_other, (
        f'"{title}" (position {pos_title}) should be before '
        f'"{other}" (position {pos_other})'
    )


# Then I should see pagination controls
@then('I should see pagination controls')
def _pagination(page):
    loc = page.locator('.pagination, .page-item')
    if loc.count() == 0 and page.locator('.post-item').count() <= 10:
        return
    assert loc.is_visible(), 'Pagination not visible'


# =============================================================================
# DASHBOARD STEPS
# =============================================================================

# Given there are multiple registered users
@given('there are multiple registered users')
def _multi_users():
    for uname in ['dashboard_user1', 'dashboard_user2']:
        User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@test.com'})


# Then I should see the users table
@then('I should see the users table')
def _table_visible(page):
    loc = page.locator('.users-table')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), 'Users table not visible'


# Then the table should contain the user 
@then(parsers.parse('the table should contain the user "{username}"'))
def _table_has_user(page, username):
    loc = page.locator(f'.users-table:has-text("{username}")')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), f'User "{username}" not in table'


# Then my row should be highlighted
@then('my row should be highlighted')
def _row_highlighted(page):
    assert page.locator('tr.current-user').is_visible(), 'Current user row not highlighted'


# Then my row should show a 
@then('my row should show a "You" badge')
def _you_badge(page):
    assert page.locator('.badge:has-text("You")').is_visible(), '"You" badge not visible'


# Then the table should have a column 
@then(parsers.parse('the table should have a column "{name}"'))
def _column_exists(page, name):
    assert page.locator(f'.users-table th:has-text("{name}")').is_visible(), f'Column "{name}" not found'


# =============================================================================
# WEIGHT DATA STEPS
# =============================================================================

# Then I should see an upload form for body measurement images
@then('I should see an upload form for body measurement images')
def _upload_form(page):
    assert (page.locator('form input[type="file"]').is_visible() or
            page.locator('form[enctype="multipart/form-data"]').is_visible()), 'Upload form not visible'


# Then I should see a list of weight records
@then('I should see a list of weight records')
def _weight_list(page):
    loc = page.locator('table, .weight-list')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), 'Weight records list not visible'


# Then I should see measurement date values
@then('I should see measurement date values')
def _date_col(page):
    assert page.locator('table th:has-text("Date")').is_visible(), 'Date column not visible'


# Then I should see weight values
@then('I should see weight values')
def _weight_col(page):
    assert page.locator('table th:has-text("Weight")').is_visible(), 'Weight column not visible'


# Then I should see BMI values
@then('I should see BMI values')
def _bmi_col(page):
    assert page.locator('table th:has-text("BMI")').is_visible(), 'BMI column not visible'


# =============================================================================
# ADMIN STEPS
# =============================================================================

# Then I should see 
@then('I should see "Django administration"')
def _admin_title(page):
    assert page.locator('text=Django administration').is_visible(), 'Admin title not visible'


# Then I should see 
@then('I should see "User Management"')
def _user_mgmt(page):
    assert page.locator('text=User Management').is_visible(), 'User Management title not visible'


# Then I should see an edit form for user details
@then('I should see an edit form for user details')
def _edit_form(page):
    assert page.locator('form').is_visible(), 'Edit form not visible'


# =============================================================================
# I18N / LANGUAGE STEPS
# =============================================================================

# Given I switch the language to 
@given(parsers.parse('I switch the language to "{language}"'))

# When I switch the language to 
@when(parsers.parse('I switch the language to "{language}"'))
def _switch_lang(page, language):
    lang_map = {'Chinese': 'zh-hans', 'English': 'en'}
    page.select_option('.lang-switcher select', lang_map.get(language, language))
    page.wait_for_load_state('networkidle')


# Then the language switcher should be present
@then('the language switcher should be present')
def _lang_switcher(page):
    assert page.locator('.lang-switcher').is_visible(), 'Language switcher not visible'


# Then the page should display text in {language}
@then(parsers.parse('the page should display text in {language}'))
def _page_lang(page, language):
    checks = {'Chinese': ['首页', '帖子', '登录'], 'English': ['Home', 'Posts', 'Login']}
    for phrase in checks.get(language, checks['English']):
        if page.locator(f'text={phrase}').first.is_visible():
            return
    raise AssertionError(f'No {language} text found')


# =============================================================================
# ADDITIONAL STEPS (merged from auth_steps.py, post_steps.py, dashboard_steps.py,
# weight_steps.py, common_steps.py)
# =============================================================================

# --- Auth specific ---

# Then I should see a welcome message containing 
@then(parsers.parse('I should see a welcome message containing "{text}"'))
def _welcome_message(page, text):
    assert page.locator(f'.hero:has-text("{text}")').is_visible(), \
        f'Welcome message with "{text}" not visible'


# Then I should see a login error message
@then('I should see a login error message')
def _login_error_visible(page):
    locator = page.locator('.alert-error').first
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), 'Login error not visible'


# Then I should see a registration error
@then('I should see a registration error')
def _register_error_visible(page):
    locators = ['.alert-error', '.error-text', '.errorlist']
    for sel in locators:
        if page.locator(sel).is_visible():
            return
    raise AssertionError('No registration error visible')


# Then the dashboard should display my username 
@then(parsers.parse('the dashboard should display my username "{username}"'))
def _dashboard_shows_username(page, username):
    content_text = page.text_content('.hero') or ''
    assert username in content_text, f'Username "{username}" not in dashboard'


# --- Post specific ---

# Then I should see the author 
@then(parsers.parse('I should see the author "{username}" on the post'))
def _author_on_post(page, username):
    detail = page.locator('.post-detail-section')
    assert detail.locator(f':has-text("{username}")').is_visible(), \
        f'Author "{username}" not on post detail'


# Then the post list should contain {count:d} posts
@then(parsers.parse('the post list should contain {count:d} posts'))
def _post_count(page, count):
    items = page.locator('.post-item')
    assert items.count() == count, f'Expected {count} posts, got {items.count()}'


# --- Dashboard specific ---

# Then the IP Address column should show a value
@then('the IP Address column should show a value')
def _ip_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    has_ip = any('.' in cell and cell.count('.') == 3 for cell in cells)
    assert has_ip, f'No IP address found in table cells: {cells[:10]}'


# Then the Login Location column should show a location
@then('the Login Location column should show a location')
def _location_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    non_empty = [c for c in cells if len(c.strip()) > 2 and c.strip() != '—']
    assert len(non_empty) > 0, 'No location values found in table'


# --- Weight specific ---

# When I upload the image 
@when(parsers.parse('I upload the image "{filename}"'))
def _upload_image(page, live_server_url, filename):
    file_input = page.locator('input[type="file"]')
    file_input.wait_for(state='visible')
    file_input.set_input_files(filename)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# --- Click / UI actions ---

# When I click the logo
@when('I click the logo')
def _click_logo(page):
    page.click('.logo')


# When I click 
@when(parsers.parse('I click "{link_text}"'))
def _click_link(page, link_text):
    link = page.locator(f'a:has-text("{link_text}")')
    link.wait_for(state='visible')
    link.click()


# When I click the nav link 
@when(parsers.parse('I click the nav link "{link_text}"'))

# When I click the 
@when(parsers.parse('I click the "{button_text}" button'))

# When I click the user 
@when(parsers.parse('I click the user "{username}"'))
def _click_element(page, link_text=None, button_text=None, username=None):
    text = link_text or button_text or username
    sel = 'nav a' if link_text else ('button' if button_text else 'a')
    link = page.locator(f'{sel}:has-text("{text}")')
    link.wait_for(state='visible')
    link.click()
    page.wait_for_load_state('networkidle')


# When I click the language switcher
@when('I click the language switcher')
def _click_lang_switcher(page):
    page.click('.lang-switcher select')


# --- Assertions ---

# Then I should not see 
@then(parsers.parse('I should not see "{text}"'))
def _should_not_see_text(page, text):
    assert page.locator(f'text={text}').count() == 0, \
        f'Text "{text}" should NOT be visible but it is'


# Then the current page URL should contain 
@then(parsers.parse('the current page URL should contain "{fragment}"'))
def _url_contains(page, fragment):
    assert fragment in page.url, f'URL {page.url} does not contain "{fragment}"'


# --- Multi-page assertions ---

# Then every page should have a working nav bar with 
@then(parsers.parse('every page should have a working nav bar with "{link}"'))
def _every_page_nav(page, live_server_url, link):
    urls = ['/', '/login/', '/register/', '/posts/']
    for url in urls:
        page.goto(live_server_url + url)
        page.wait_for_load_state('networkidle')
        assert page.locator(f'nav a:has-text("{link}")').is_visible(), \
            f'Nav link "{link}" missing on {url}'


# --- Textarea helper ---

# When I fill textarea 
@when(parsers.parse('I fill textarea "{field}" with "{value}"'))
def _fill_textarea(page, field, value):
    page.wait_for_selector(f'textarea[name="{field}"]', state='visible')
    page.fill(f'textarea[name="{field}"]', value)

