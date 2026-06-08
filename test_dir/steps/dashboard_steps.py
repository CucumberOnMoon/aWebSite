"""Step definitions for the dashboard / user table feature."""

from pytest_bdd import step, parsers


@step(parsers.parse('there are multiple registered users'), type_=None)
def multiple_users(page):
    """Register a second user while keeping the current login."""
    page.goto(page._base_url + '/register/')
    if '/success/' not in page.url:
        page.fill('input[name="username"]', 'dashboard_user1')
        page.fill('input[name="password1"]', 'TestPass123!')
        page.fill('input[name="password2"]', 'TestPass123!')
        page.click('button[type="submit"]')
        page.wait_for_url('**/success/')

    page.goto(page._base_url + '/logout/')
    page.wait_for_load_state('networkidle')
    page.goto(page._base_url + '/register/')
    page.fill('input[name="username"]', 'dashboard_user2')
    page.fill('input[name="password1"]', 'TestPass123!')
    page.fill('input[name="password2"]', 'TestPass123!')
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/')


@step('I should see the users table', type_=None)
def users_table_visible(page):
    assert page.locator('.users-table').is_visible(), 'Users table not visible'


@step(parsers.parse('the table should contain the user "{username}"'), type_=None)
def table_contains_user(page, username):
    assert page.locator(f'.users-table:has-text("{username}")').is_visible(), \
        f'User "{username}" not in table'


@step('my row should be highlighted', type_=None)
def current_user_highlighted(page):
    assert page.locator('tr.current-user').is_visible(), 'Current user row not highlighted'


@step('my row should show a "You" badge', type_=None)
def you_badge_visible(page):
    assert page.locator('.badge:has-text("You")').is_visible(), '"You" badge not visible'


@step(parsers.parse('the table should have a column "{column_name}"'), type_=None)
def column_exists(page, column_name):
    assert page.locator(f'.users-table th:has-text("{column_name}")').is_visible(), \
        f'Column "{column_name}" not found'


@step('the IP Address column should show a value', type_=None)
def ip_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    has_ip = any('.' in cell and cell.count('.') == 3 for cell in cells)
    assert has_ip, f'No IP address found in table cells: {cells[:10]}'


@step('the Login Location column should show a location', type_=None)
def location_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    non_empty = [c for c in cells if len(c.strip()) > 2 and c.strip() != '—']
    assert len(non_empty) > 0, 'No location values found in table'
