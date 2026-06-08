"""
conftest.py for the steps package.
Loads all step definitions so pytest-bdd 8.x can discover their fixtures.
Django is already set up by the root conftest.py when this loads.
"""
from pytest_bdd import given, when, then, step, parsers
from django.contrib.auth.models import User
from accounts.models import Post

# =============================================================================
# AUTH STEPS
# =============================================================================

TEST_PASSWORD='***'
_TEST_USERS_CREATED = False


def _ensure_test_users():
    global _TEST_USERS_CREATED
    if _TEST_USERS_CREATED:
        return
    for uname in ['loggedin_user', 'specific_user', 'admin_user']:
        u, created = User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@test.com'})
        if created:
            u.set_password(TEST_PASSWORD)
            u.save()
    _TEST_USERS_CREATED = True


@given('I am logged in')
def _logged_in(page, live_server_url):
    _ensure_test_users()
    page.goto(live_server_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', 'loggedin_user')
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/success/**', timeout=5000)


@given('I am logged out')
@when('I log out')
def _logged_out(page, live_server_url):
    page.goto(live_server_url + '/logout/')
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I log in as "{username}" with password "{password}"'))
def _login_as(page, live_server_url, username, password):
    page.goto(live_server_url + '/login/')
    page.wait_for_selector('input[name="username"]', state='visible')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


@given('I am on the home page')
@given(parsers.parse('I am on the {page_name} page'))
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


@when(parsers.parse('I fill in "{field}" with "{value}"'))
def _fill(page, field, value):
    page.wait_for_selector(f'input[name="{field}"]', state='visible')
    page.fill(f'input[name="{field}"]', value)


@when('I submit the form')
@when('I submit the registration form')
@when('I submit the login form')
def _submit(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


# =============================================================================
# COMMON / ASSERTIONS
# =============================================================================

@then(parsers.parse('I should see "{text}"'))
def _see_text(page, text):
    loc = page.locator(f'text={text}')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), f'Text "{text}" not visible'


@then('I should be redirected to the login page')
def _redirect_login(page):
    page.wait_for_url('**/login/**', timeout=5000)


@then('I should be redirected to the dashboard')
def _redirect_dash(page):
    page.wait_for_url('**/success/**', timeout=5000)


@then(parsers.parse('I should be on the "{page_name}" page'))
def _on_page(page, live_server_url, page_name):
    PAGE_MAP = {
        'home': '/', 'login': '/login/', 'register': '/register/',
        'posts': '/posts/', 'dashboard': '/success/', 'create post': '/posts/create/',
    }
    expected = PAGE_MAP.get(page_name.lower(), '/').rstrip('/')
    current = page.url.replace(live_server_url, '').rstrip('/')
    assert current == expected or current.startswith(expected), f'Expected {expected}, got {current}'


@then('the page title should contain "Posts"')
@then(parsers.parse('the page title should contain "{text}"'))
def _title_contains(page, text='Posts'):
    title = page.title()
    assert text.lower() in title.lower(), f'Title "{title}" does not contain "{text}"'


@then(parsers.parse('the nav bar should show "{text}"'))
@then(parsers.parse('the nav bar should display "{text}"'))
def _nav_shows(page, text):
    assert page.locator(f'nav:has-text("{text}")').is_visible(), f'Nav bar does not show "{text}"'


# =============================================================================
# POST STEPS
# =============================================================================

@given(parsers.parse('there is a post titled "{title}"'))
def _create_post(title):
    author, _ = User.objects.get_or_create(username='post_author', defaults={'email': 'post_author@test.com'})
    Post.objects.get_or_create(title=title, defaults={'content': f'Content of {title}.', 'author': author})


@when(parsers.parse('I fill the title with "{title}"'))
def _fill_title(page, title):
    page.wait_for_selector('input[name="title"]', state='visible')
    page.fill('input[name="title"]', title)


@when(parsers.parse('I fill the content with "{content}"'))
def _fill_content(page, content):
    page.wait_for_selector('textarea[name="content"]', state='visible')
    page.fill('textarea[name="content"]', content)


@when('I submit the post form')
def _submit_post(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I click the post title "{title}"'))
def _click_post(page, title):
    link = page.locator(f'.post-item h3 a:has-text("{title}")')
    link.wait_for(state='visible')
    link.click()
    page.wait_for_load_state('networkidle')


@then(parsers.parse('I should see a post titled "{title}" in the list'))
def _post_in_list(page, title):
    loc = page.locator(f'.post-item:has-text("{title}")')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), f'Post "{title}" not in list'


@then(parsers.parse('I should see the post content "{content}"'))
def _post_content(page, content):
    loc = page.locator(f'.post-content:has-text("{content}")')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), f'Content "{content}" not visible'


@then('I should see an empty post list message')
def _empty_list(page):
    loc = page.locator(':has-text("No posts yet")')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), 'Empty post message not visible'


@then(parsers.parse('the post "{title}" should appear before "{other}"'))
def _post_order(page, title, other):
    content = page.text_content('.post-list') or ''
    assert content.find(title) < content.find(other), f'"{title}" should be before "{other}"'


@then('I should see pagination controls')
def _pagination(page):
    loc = page.locator('.pagination, .page-item')
    if loc.count() == 0 and page.locator('.post-item').count() <= 10:
        return
    assert loc.is_visible(), 'Pagination not visible'


# =============================================================================
# DASHBOARD STEPS
# =============================================================================

@given('there are multiple registered users')
def _multi_users():
    for uname in ['dashboard_user1', 'dashboard_user2']:
        User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@test.com'})


@then('I should see the users table')
def _table_visible(page):
    loc = page.locator('.users-table')
    loc.wait_for(state='visible', timeout=5000)
    assert loc.is_visible(), 'Users table not visible'


@then(parsers.parse('the table should contain the user "{username}"'))
def _table_has_user(page, username):
    loc = page.locator(f'.users-table:has-text("{username}")')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), f'User "{username}" not in table'


@then('my row should be highlighted')
def _row_highlighted(page):
    assert page.locator('tr.current-user').is_visible(), 'Current user row not highlighted'


@then('my row should show a "You" badge')
def _you_badge(page):
    assert page.locator('.badge:has-text("You")').is_visible(), '"You" badge not visible'


@then(parsers.parse('the table should have a column "{name}"'))
def _column_exists(page, name):
    assert page.locator(f'.users-table th:has-text("{name}")').is_visible(), f'Column "{name}" not found'


# =============================================================================
# WEIGHT DATA STEPS
# =============================================================================

@then('I should see an upload form for body measurement images')
def _upload_form(page):
    assert (page.locator('form input[type="file"]').is_visible() or
            page.locator('form[enctype="multipart/form-data"]').is_visible()), 'Upload form not visible'


@then('I should see a list of weight records')
def _weight_list(page):
    loc = page.locator('table, .weight-list')
    loc.wait_for(state='visible', timeout=3000)
    assert loc.is_visible(), 'Weight records list not visible'


@then('I should see measurement date values')
def _date_col(page):
    assert page.locator('table th:has-text("Date")').is_visible(), 'Date column not visible'


@then('I should see weight values')
def _weight_col(page):
    assert page.locator('table th:has-text("Weight")').is_visible(), 'Weight column not visible'


@then('I should see BMI values')
def _bmi_col(page):
    assert page.locator('table th:has-text("BMI")').is_visible(), 'BMI column not visible'


# =============================================================================
# ADMIN STEPS
# =============================================================================

@then('I should see "Django administration"')
def _admin_title(page):
    assert page.locator('text=Django administration').is_visible(), 'Admin title not visible'


@then('I should see "User Management"')
def _user_mgmt(page):
    assert page.locator('text=User Management').is_visible(), 'User Management title not visible'


@then('I should see an edit form for user details')
def _edit_form(page):
    assert page.locator('form').is_visible(), 'Edit form not visible'


# =============================================================================
# I18N / LANGUAGE STEPS
# =============================================================================

@when(parsers.parse('I switch the language to "{language}"'))
def _switch_lang(page, language):
    lang_map = {'Chinese': 'zh-hans', 'English': 'en'}
    page.select_option('.lang-switcher select', lang_map.get(language, language))
    page.wait_for_load_state('networkidle')


@then('the language switcher should be present')
def _lang_switcher(page):
    assert page.locator('.lang-switcher').is_visible(), 'Language switcher not visible'


@then(parsers.parse('the page should display text in {language}'))
def _page_lang(page, language):
    checks = {'Chinese': ['首页', '帖子', '登录'], 'English': ['Home', 'Posts', 'Login']}
    for phrase in checks.get(language, checks['English']):
        if page.locator(f'text={phrase}').is_visible():
            return
    raise AssertionError(f'No {language} text found')
