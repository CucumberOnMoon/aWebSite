"""
Step definitions for the dashboard / user table feature.
Uses Django ORM for user creation.
"""

from pytest_bdd import given, then, parsers
from django.contrib.auth.models import User


@given('there are multiple registered users')
def multiple_users(page):
    for username in ['dashboard_user1', 'dashboard_user2']:
        User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@test.com'},
        )


@then('I should see the users table')
def users_table_visible(page):
    locator = page.locator('.users-table')
    locator.wait_for(state='visible', timeout=5000)
    assert locator.is_visible(), 'Users table not visible'


@then(parsers.parse('the table should contain the user "{username}"'))
def table_contains_user(page, username):
    locator = page.locator(f'.users-table:has-text("{username}")')
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), f'User "{username}" not in table'


@then('my row should be highlighted')
def current_user_highlighted(page):
    assert page.locator('tr.current-user').is_visible(), \
        'Current user row not highlighted'


@then('my row should show a "You" badge')
def you_badge_visible(page):
    assert page.locator('.badge:has-text("You")').is_visible(), \
        '"You" badge not visible'


@then(parsers.parse('the table should have a column "{column_name}"'))
def column_exists(page, column_name):
    assert page.locator(f'.users-table th:has-text("{column_name}")').is_visible(), \
        f'Column "{column_name}" not found'


@then('the IP Address column should show a value')
def ip_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    has_ip = any('.' in cell and cell.count('.') == 3 for cell in cells)
    assert has_ip, f'No IP address found in table cells: {cells[:10]}'


@then('the Login Location column should show a location')
def location_column_populated(page):
    cells = page.locator('.users-table td').all_text_contents()
    non_empty = [c for c in cells if len(c.strip()) > 2 and c.strip() != '—']
    assert len(non_empty) > 0, 'No location values found in table'
