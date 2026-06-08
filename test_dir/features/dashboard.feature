Feature: User Dashboard
    As a logged-in user
    I want to view the dashboard with a user table
    So that I can see all registered users and their last login details

    Scenario: Dashboard shows personal info cards
        Given I am logged in
        When I am on the dashboard page
        Then I should see "Login Successful!"
        And I should see "Username"
        And I should see "Email"
        And I should see "Date Joined"

    Scenario: Dashboard shows a table of all users
        Given I am logged in
        When I am on the dashboard page
        Then I should see the users table
        And I should see "All Users"

    Scenario: Current user row is highlighted with a badge
        Given I am logged in
        When I am on the dashboard page
        Then my row should be highlighted
        And my row should show a "You" badge

    Scenario: Table shows multiple registered users
        Given there are multiple registered users
        When I am on the dashboard page
        Then the table should contain the user "dashboard_user1"
        And the table should contain the user "dashboard_user2"

    Scenario: Table includes IP and Location columns
        Given I am logged in
        When I am on the dashboard page
        Then the table should have a column "IP Address"
        And the table should have a column "Login Location"

    Scenario: Chinese dashboard translations
        Given I am logged in
        When I am on the dashboard page
        And I switch the language to "Chinese"
        Then I should see "登录成功！"
        And I should see "所有用户"
