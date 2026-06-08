Feature: User Authentication
    As a visitor
    I want to register, log in, and log out
    So that I can access protected features

    Background:
        Given I am logged out

    Scenario: Register a new account successfully
        When I am on the register page
        And I fill in "username" with "testuser01"
        And I fill in "password1" with "TestPass123!"
        And I fill in "password2" with "TestPass123!"
        And I submit the registration form
        Then I should be on the "posts" page

    Scenario: Register with a duplicate username
        Given I am on the register page
        And I fill in "username" with "testuser01"
        And I fill in "password1" with "StrongPass99!"
        And I fill in "password2" with "StrongPass99!"
        When I submit the registration form
        Then I should see a registration error

    Scenario: Login with valid credentials
        Given I am logged out
        When I log in as "loggedin_user" with password "TestPass123!"
        Then I should be on the "posts" page

    Scenario: Login with invalid credentials
        When I am on the login page
        And I fill in "username" with "nobody"
        And I fill in "password" with "wrongpassword"
        And I submit the login form
        Then I should see a login error message

    Scenario: Logout redirects to home
        Given I am logged in
        When I log out
        Then I should be on the "home" page

    Scenario: Dashboard requires authentication
        When I am on the dashboard page
        Then I should be redirected to the login page
