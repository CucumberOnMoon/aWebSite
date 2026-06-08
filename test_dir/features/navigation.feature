Feature: Navigation and Language Switching
    As a visitor
    I want to navigate the site and switch languages
    So that I can use the site in my preferred language

    Scenario: Homepage shows correct elements for guests
        When I am on the home page
        Then I should see "Welcome to MySite"
        And the nav bar should show "Login"
        And the nav bar should show "Register"
        And the nav bar should show "Posts"

    Scenario: Homepage shows correct elements for authenticated users
        Given I am logged in
        When I am on the home page
        Then the nav bar should show "Dashboard"
        And the nav bar should show "Logout"

    Scenario: Nav bar has Posts link on every page
        When I am on the home page
        Then the nav bar should display "Posts"
        When I am on the login page
        Then the nav bar should display "Posts"
        When I am on the register page
        Then the nav bar should display "Posts"
        When I am on the posts page
        Then the nav bar should display "Posts"

    Scenario: Language switcher is present on all pages
        When I am on the home page
        Then the language switcher should be present
        When I am on the login page
        Then the language switcher should be present
        When I am on the register page
        Then the language switcher should be present

    Scenario: Switch site language to Chinese
        When I am on the home page
        And I switch the language to "Chinese"
        Then the page should display text in Chinese

    Scenario: Switch language back to English
        When I am on the home page
        And I switch the language to "Chinese"
        And I switch the language to "English"
        Then the page should display text in English

    Scenario: Language switch persists across page navigation
        When I am on the home page
        And I switch the language to "Chinese"
        And I click the nav link "Posts"
        Then the page should display text in Chinese
