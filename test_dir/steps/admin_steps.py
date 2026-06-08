"""
Step definitions for Django admin and user management features.
"""

from pytest_bdd import then, parsers


@then('I should see "Django administration"')
def django_admin_title(page):
    assert page.locator('text=Django administration').is_visible(), \
        'Django admin title not visible'


@then('I should see "User Management"')
def user_management_title(page):
    assert page.locator('text=User Management').is_visible(), \
        'User Management title not visible'


@then('I should see an edit form for user details')
def edit_form_visible(page):
    assert page.locator('form').is_visible(), 'Edit form not visible'
