"""Step definitions for authentication features."""

from pytest_bdd import step, parsers


@step(parsers.parse('I fill in "{field}" with "{value}"'), type_=None)
def fill_field(page, field, value):
    page.fill(f'input[name="{field}"]', value)


@step('I submit the registration form', type_=None)
def submit_register(page):
    page.click('button[type="submit"]')


@step('I submit the login form', type_=None)
def submit_login(page):
    page.click('button[type="submit"]')


@step('I log out', type_=None)
def log_out(page):
    page.goto(page._base_url + '/logout/')
    page.wait_for_load_state('networkidle')


@step(parsers.parse('I should see a welcome message containing "{text}"'), type_=None)
def welcome_message(page, text):
    assert page.locator(f'.hero:has-text("{text}")').is_visible(), \
        f'Welcome message with "{text}" not visible'


@step('I should see a login error message', type_=None)
def login_error_visible(page):
    assert page.locator('.alert-error').is_visible(), 'Login error not visible'


@step('I should see a registration error', type_=None)
def register_error_visible(page):
    assert (page.locator('.alert-error').is_visible() or
            page.locator('.error-text').is_visible()), \
        'Registration error not visible'


@step(parsers.parse('the dashboard should display my username "{username}"'), type_=None)
def dashboard_shows_username(page, username):
    content = page.text_content('.hero')
    assert username in content, f'Username "{username}" not in dashboard'


@step('I should be redirected to the login page', type_=None)
def redirected_to_login(page):
    assert '/login/' in page.url, f'Not on login page: {page.url}'


@step('I should be redirected to the dashboard', type_=None)
def redirected_to_dashboard(page):
    assert '/success/' in page.url, f'Not on dashboard: {page.url}'
