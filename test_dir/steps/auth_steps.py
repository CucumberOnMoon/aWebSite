"""
Step definitions for authentication features.
"""

from pytest_bdd import then, parsers


@then(parsers.parse('I should see a welcome message containing "{text}"'))
def welcome_message(page, text):
    assert page.locator(f'.hero:has-text("{text}")').is_visible(), \
        f'Welcome message with "{text}" not visible'


@then('I should see a login error message')
def login_error_visible(page):
    locator = page.locator('.alert-error')
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), 'Login error not visible'


@then('I should see a registration error')
def register_error_visible(page):
    locators = ['.alert-error', '.error-text', '.errorlist']
    for sel in locators:
        if page.locator(sel).is_visible():
            return
    raise AssertionError('No registration error visible')


@then(parsers.parse('the dashboard should display my username "{username}"'))
def dashboard_shows_username(page, username):
    content = page.text_content('.hero') or ''
    assert username in content, f'Username "{username}" not in dashboard'
