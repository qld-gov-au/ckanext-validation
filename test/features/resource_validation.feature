Feature: Resource validation

    Scenario: As an editor, I can create a resource with an uploaded validation schema
        Given "TestOrgEditor" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I press the element with xpath "//form[@id='resource-edit']//a[string() = 'Link']"
        And I fill in "name" with "Test resource"
        And I attach the file "test.csv" to "upload"
        And I fill in "description" with "Testing validation schema"
        And I attach the file "test_schema.json" to "schema_upload"
        And I press the element with xpath "//button[contains(string(), 'Add')]"
        Then I should see "Test resource"
        When I click the link with text that contains "Test resource"
        And I click the link with text that contains "Manage"
        Then I should see "\"fields\": ["
        And I should see "\"name\": \"field1\""
        And I should see "\"name\": \"field2\""
