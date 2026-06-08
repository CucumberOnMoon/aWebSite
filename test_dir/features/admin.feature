Feature: Django Admin Interface
    As a staff user
    I want to access the Django admin to manage site content
    So that I can moderate posts and users

    Scenario: Admin login page loads
        When I am on the "admin" page
        Then the page title should contain "Admin"

    Scenario: Admin requires login
        When I am on the "admin" page
        Then I should see "Django administration"

    Scenario: Guest cannot access user management
        Given I am logged out
        When I am on the "users" page
        Then I should be redirected to the login page

    Scenario: Create a new user via user management
        Given I am logged in
        When I am on the "users" page
        Then I should see "User Management"

    Scenario: Edit user page shows form
        Given I am logged in
        When I click the user "loggedin_user"
        And I am on the users page
        Then I should see an edit form for user details
