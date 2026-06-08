"""
Shared step definitions — navigation, auth state, common assertions, waits.
Merged from common_steps.py + nav_steps.py with dedup and ORM support.

Uses @given/@when/@then for strict type matching (pytest-bdd 8.x).
"""

import pytest
from pytest_bdd import given, when, then, step, parsers
from django.contrib.auth.models import User


# ═════════════════════════════════════════════════════════════════════════════
# Navigation
# ═════════════════════════════════════════════════════════════════════════════

PAGE_MAP = {
    'home': '/',
    'login': '/login/',
    'register': '/register/',
    'posts': '/posts/',
    'dashboard': '/success/',
    'create post': '/posts/create/',
    'weight data': '/weight-data/',
    'users': '/users/',
    'admin': '/admin/',
}


@given(parsers.parse('I am on the {page_name} page'))
def go_to_page_given(page, page_name):
    url = PAGE_MAP.get(page_name.lower(), '/')
    page.goto(page._base_url + url)
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I am on the {page_name} page'))
def go_to_page_when(page, page_name):
    url = PAGE_MAP.get(page_name.lower(), '/')
    page.goto(page._base_url + url)
    page.wait_for_load_state('networkidle')


# ═════════════════════════════════════════════════════════════════════════════
# Auth — uses Django ORM for fast setup, UI for actual login flow
# ═════════════════════════════════════════════════════════════════════════════

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


@given('I am logged in')
def ensure_logged_in(page):
    _ensure_test_users()
    page.goto(page._base_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', 'loggedin_user')
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/**')


@given('I am logged in as a specific user')
def login_specific_user(page):
    _ensure_test_users()
    page.goto(page._base_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', 'specific_user')
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/**')


@when(parsers.parse('I log in as "{username}" with password "{password}"'))
def login_as(page, username, password):
    page.goto(page._base_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


@step('I am logged out', type_=None)
def ensure_logged_out(page):
    page.goto(page._base_url + '/logout/')
    page.wait_for_load_state('networkidle')


@when('I log out')
def log_out_action(page):
    page.goto(page._base_url + '/logout/')
    page.wait_for_load_state('networkidle')


# ═════════════════════════════════════════════════════════════════════════════
# Form helpers
# ═════════════════════════════════════════════════════════════════════════════

@when(parsers.parse('I fill in "{field}" with "{value}"'))
def fill_field(page, field, value):
    page.wait_for_selector(f'input[name="{field}"]', state='visible')
    page.fill(f'input[name="{field}"]', value)


@when(parsers.parse('I fill textarea "{field}" with "{value}"'))
def fill_textarea(page, field, value):
    page.wait_for_selector(f'textarea[name="{field}"]', state='visible')
    page.fill(f'textarea[name="{field}"]', value)


@when('I submit the form')
@when('I submit the registration form')
@when('I submit the login form')
def submit_form(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# ═════════════════════════════════════════════════════════════════════════════
# Click actions
# ═════════════════════════════════════════════════════════════════════════════

@when('I click the logo')
def click_logo(page):
    page.click('.logo')


@when(parsers.parse('I click "{link_text}"'))
def click_link(page, link_text):
    link = page.locator(f'a:has-text("{link_text}")')
    link.wait_for(state='visible')
    link.click()


@when(parsers.parse('I click the "{button_text}" button'))
@when(parsers.parse('I click the nav link "{link_text}"'))
@when(parsers.parse('I click the user "{username}"'))
def click_element(page, link_text=None, button_text=None, username=None):
    text = link_text or button_text or username
    sel = 'nav a' if link_text else ('button' if button_text else 'a')
    link = page.locator(f'{sel}:has-text("{text}")')
    link.wait_for(state='visible')
    link.click()


# ═════════════════════════════════════════════════════════════════════════════
# Assertions
# ═════════════════════════════════════════════════════════════════════════════

@then('the page title should contain "Posts"')
def page_title_contains_posts(page):
    title = page.title()
    assert 'posts' in title.lower(), f'Title "{title}" does not contain "Posts"'


@then(parsers.parse('the page title should contain "{text}"'))
def page_title_contains_text(page, text):
    title = page.title()
    assert text.lower() in title.lower(), f'Title "{title}" does not contain "{text}"'


@then(parsers.parse('I should see "{text}"'))
def should_see_text(page, text):
    locator = page.locator(f'text={text}')
    locator.wait_for(state='visible', timeout=5000)
    assert locator.is_visible(), f'Text "{text}" not visible'


@then(parsers.parse('I should not see "{text}"'))
def should_not_see_text(page, text):
    assert page.locator(f'text={text}').count() == 0, \
        f'Text "{text}" should NOT be visible but it is'


@then(parsers.parse('I should be on the "{page_name}" page'))
def should_be_on_page(page, page_name):
    expected = PAGE_MAP.get(page_name.lower(), '/').rstrip('/')
    current = page.url.replace(page._base_url, '').rstrip('/')
    assert current == expected or current.startswith(expected), \
        f'Expected path {expected}, got {current}'


@then('I should be redirected to the login page')
def redirected_to_login(page):
    page.wait_for_url('**/login/**', timeout=5000)


@then('I should be redirected to the dashboard')
def redirected_to_dashboard(page):
    page.wait_for_url('**/success/**', timeout=5000)


@then(parsers.parse('the nav bar should show "{text}"'))
@then(parsers.parse('the nav bar should display "{text}"'))
def nav_bar_shows(page, text):
    assert page.locator(f'nav:has-text("{text}")').is_visible(), \
        f'Nav bar does not show "{text}"'


@then(parsers.parse('the current page URL should contain "{fragment}"'))
def url_contains(page, fragment):
    assert fragment in page.url, f'URL {page.url} does not contain "{fragment}"'


# ═════════════════════════════════════════════════════════════════════════════
# Language / i18n
# ═════════════════════════════════════════════════════════════════════════════

@when(parsers.parse('I switch the language to "{language}"'))
def switch_language(page, language):
    lang_map = {
        'Chinese': 'zh-hans',
        'English': 'en',
        '简体中文': 'zh-hans',
    }
    lang_code = lang_map.get(language, language)
    page.select_option('.lang-switcher select', lang_code)
    page.wait_for_load_state('networkidle')


@when('I click the language switcher')
def click_lang_switcher(page):
    page.click('.lang-switcher select')


@then(parsers.parse('the page should display text in {language}'))
def page_in_language(page, language):
    checks = {
        'Chinese': ['首页', '帖子', '登录', '注册'],
        'English': ['Home', 'Posts', 'Login', 'Register'],
    }
    for phrase in checks.get(language, checks['English']):
        if page.locator(f'text={phrase}').is_visible():
            return
    all_text = page.text_content('body') or ''
    raise AssertionError(
        f'No {language} text found. Body (first 300): {all_text[:300]}'
    )


@given('the language switcher should be present')
@then('the language switcher should be present')
def lang_switcher_present(page):
    assert page.locator('.lang-switcher').is_visible(), \
        'Language switcher not visible'


@then(parsers.parse('every page should have a working nav bar with "{link}"'))
def every_page_nav(page, link):
    urls = ['/', '/login/', '/register/', '/posts/']
    for url in urls:
        page.goto(page._base_url + url)
        page.wait_for_load_state('networkidle')
        assert page.locator(f'nav a:has-text("{link}")').is_visible(), \
            f'Nav link "{link}" missing on {url}'
