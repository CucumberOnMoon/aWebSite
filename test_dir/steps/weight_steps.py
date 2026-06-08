"""
Step definitions for weight-data / body measurement features.
"""

from pytest_bdd import then, when, parsers


@then('I should see an upload form for body measurement images')
def upload_form_visible(page):
    assert page.locator('form input[type="file"]').is_visible() or \
           page.locator('form[enctype="multipart/form-data"]').is_visible(), \
        'Upload form not visible'


@then('I should see a list of weight records')
def weight_records_visible(page):
    locator = page.locator('table, .weight-list, .measurement-list')
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), 'Weight records list not visible'


@then('I should see measurement date values')
def measurement_date_visible(page):
    assert page.locator('table th:has-text("Date"), .measurement-date').is_visible(), \
        'Date column not visible'


@then('I should see weight values')
def weight_values_visible(page):
    assert page.locator('table th:has-text("Weight"), .weight-value').is_visible(), \
        'Weight column not visible'


@then('I should see BMI values')
def bmi_values_visible(page):
    assert page.locator('table th:has-text("BMI"), .bmi-value').is_visible(), \
        'BMI column not visible'


@when(parsers.parse('I upload the image "{filename}"'))
def upload_image(page, filename):
    file_input = page.locator('input[type="file"]')
    file_input.wait_for(state='visible')
    file_input.set_input_files(filename)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
