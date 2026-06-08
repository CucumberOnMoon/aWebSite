"""Shared step definitions used across multiple feature files."""

from pytest_bdd import step, parsers


# ── Navigation ───────────────────────────────────────────────────────────────

@step(parsers.parse('I am on the {page_name} page'), type_=None)
def go_to_page(page, page_name):
    mapping = {
        'home': '/',
        'login': '/login/',
        'register': '/register/',
        'posts': '/posts/',
        'dashboard': '/success/',
        'create post': '/posts/create/',
    }
    url = mapping.get(page_name.lower(), '/')
    page.goto(page._base_url + url)


# ── Auth state ───────────────────────────────────────────────────────────────

@step('I am logged in', type_=None)
def ensure_logged_in(page):
    page.goto(page._base_url + '/register/')
    page.fill('input[name="username"]', 'loggedin_user')
    page.fill('input[name="password1"]', 'TestPass123!')
    page.fill('input[name="password2"]', 'TestPass123!')
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/')


@step('I am logged out', type_=None)
def ensure_logged_out(page):
    page.goto(page._base_url + '/logout/')
    page.wait_for_load_state('networkidle')


@step('I am logged in as a specific user', type_=None)
def login_specific_user(page):
    page.goto(page._base_url + '/register/')
    page.fill('input[name="username"]', 'specific_user')
    page.fill('input[name="password1"]', 'TestPass123!')
    page.fill('input[name="password2"]', 'TestPass123!')
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/')


# ── Click actions ────────────────────────────────────────────────────────────

@step('I click the logo', type_=None)
def click_logo(page):
    page.click('.logo')


@step(parsers.parse('I click "{link_text}"'), type_=None)
def click_link(page, link_text):
    page.click(f'a:has-text("{link_text}")')


@step(parsers.parse('I click the "{button_text}" button'), type_=None)
def click_button(page, button_text):
    page.click(f'button:has-text("{button_text}")')


@step(parsers.parse('I click the nav link "{link_text}"'), type_=None)
def click_nav_link(page, link_text):
    page.click(f'nav a:has-text("{link_text}")')


# ── Assertions ───────────────────────────────────────────────────────────────

@step(parsers.parse('the page title should contain "{text}"'), type_=None)
def page_title_contains(page, text):
    title = page.title()
    assert text.lower() in title.lower(), f'Title "{title}" does not contain "{text}"'


@step(parsers.parse('I should see "{text}"'), type_=None)
def should_see_text(page, text):
    assert page.locator(f'text={text}').is_visible(), f'Text "{text}" not visible'


@step(parsers.parse('I should be on the "{page_name}" page'), type_=None)
def should_be_on_page(page, page_name):
    mapping = {
        'home': '/',
        'login': '/login/',
        'register': '/register/',
        'posts': '/posts/',
        'dashboard': '/success/',
        'create post': '/posts/create/',
    }
    expected = mapping.get(page_name.lower(), '/')
    current = page.url.replace(page._base_url, '').rstrip('/')
    expected = expected.rstrip('/')
    assert current == expected or current.startswith(expected), \
        f'Expected {expected}, got {current}'


@step(parsers.parse('the nav bar should show "{text}"'), type_=None)
def nav_bar_contains(page, text):
    assert page.locator(f'nav:has-text("{text}")').is_visible(), \
        f'Nav bar does not contain "{text}"'
