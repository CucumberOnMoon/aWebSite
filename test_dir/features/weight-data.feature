Feature: Weight Data Management
    As a logged-in user
    I want to upload body measurement screenshots and view my history
    So that I can track my health data over time

    Background:
        Given I am logged in

    Scenario: Weight data page shows upload form
        When I am on the "weight data" page
        Then I should see "Weight Data"
        And the page title should contain "Weight"

    Scenario: Upload page accepts an image
        When I am on the "weight data" page
        Then I should see an upload form for body measurement images

    Scenario: Weight data page lists recent measurements
        Given I am on the "weight data" page
        Then I should see a list of weight records

    Scenario: Guest is redirected from weight data page
        Given I am logged out
        When I am on the "weight data" page
        Then I should be redirected to the login page

    Scenario: Weight record shows date, weight, BMI
        Given I am on the "weight data" page
        Then I should see measurement date values
        And I should see weight values
        And I should see BMI values
