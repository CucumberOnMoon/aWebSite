Feature: Blog Posts
    As a user
    I want to browse and create posts
    So that I can share content with other users

    Scenario: View an empty post list
        When I am on the posts page
        Then I should see an empty post list message

    Scenario: Create a new post
        Given I am logged in
        When I am on the create post page
        And I fill the title with "My First Blog Post"
        And I fill the content with "This is the content of my very first blog post!"
        And I submit the post form
        Then I should see the post content "This is the content of my very first blog post!"
        And I should see "My First Blog Post"

    Scenario: View a post detail after creation
        Given I am logged in
        And there is a post titled "Detail Test Post"
        When I am on the posts page
        And I click the post title "Detail Test Post"
        Then I should see "Content of Detail Test Post."

    Scenario: Multiple posts appear in the list
        Given I am logged in
        And there is a post titled "Alpha Post"
        And there is a post titled "Beta Post"
        When I am on the posts page
        Then I should see a post titled "Alpha Post" in the list
        And I should see a post titled "Beta Post" in the list
        And the post "Beta Post" should appear before "Alpha Post"

    Scenario: Guest can view posts but cannot create them
        Given I am logged out
        When I am on the posts page
        Then the page title should contain "Posts"
        When I am on the create post page
        Then I should be redirected to the login page
