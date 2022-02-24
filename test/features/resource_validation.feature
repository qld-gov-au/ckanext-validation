Feature: Resource validation

    Scenario: As an editor, I can create and update a resource with an uploaded validation schema
        Given "TestOrgEditor" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I fill in "name" with "Test validation schema"
        And I attach the file "test.csv" to "upload"
        And I fill in "description" with "Testing validation schema"
        And I attach the file "test_schema.json" to "schema_upload"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test validation schema"

        When I click the link with text that contains "Test validation schema"
        And I click the link with text that contains "Manage"
        Then I should see text containing quotes `"fields": [`
        And I should see text containing quotes `"name": "field1"`
        And I should see text containing quotes `"name": "field2"`

        When I click the link with text that contains "Test validation schema"
        And I click the link with text that contains "Manage"
        And I attach the file "test_schema2.json" to "schema_upload"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test validation schema"
        When I click the link with text that contains "Test validation schema"
        And I click the link with text that contains "Manage"
        Then I should see text containing quotes `"fields": [`
        And I should see text containing quotes `"name": "field1"`
        And I should see text containing quotes `"name": "field2"`
        And I should see text containing quotes `"title": "First column"`
        And I should see text containing quotes `"title": "Second column"`


    Scenario: As an editor, I can create and update a resource with validation options
        Given "TestOrgEditor" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I fill in "name" with "Test validation options"
        And I attach the file "test.csv" to "upload"
        And I fill in "description" with "Testing validation options"
        And I attach the file "test_schema.json" to "schema_upload"
        And I fill in "validation_options" with "{"headers": 3}"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test validation options"

        When I click the link with text that contains "Test validation options"
        And I click the link with text that contains "Manage"
        Then I should see text containing quotes `"headers": 3`

        When I click the link with text that contains "Test validation options"
        And I click the link with text that contains "Manage"
        And I fill in "validation_options" with "{"headers": 3, "delimiter": ","}"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test validation options"
        When I click the link with text that contains "Test validation options"
        And I click the link with text that contains "Manage"
        Then I should see text containing quotes `"headers": 3`
        And I should see text containing quotes `"delimiter": ","`


    Scenario: As an editor, I can upload a valid CSV and see a success status
        Given "TestOrgEditor" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I fill in "name" with "Test valid CSV"
        And I attach the file "valid.csv" to "upload"
        And I fill in "description" with "Testing validation that should pass"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test valid CSV"
        When I wait for 5 seconds
        And I click the link with text that contains "Test valid CSV"
        Then I should see "Validation status"
        And I should see "success"
        And I should not see "failure"


    Scenario: As an editor, I can upload an invalid CSV and see a failure status
        Given "TestOrgEditor" as the persona
        When I log in
        And I visit "/dataset/new_resource/warandpeace"
        And I fill in "name" with "Test invalid CSV"
        And I attach the file "valid.csv" to "upload"
        And I fill in "description" with "Testing validation with insufficient fields"
        And I press the element with xpath "//button[contains(@class, 'btn-primary')]"
        Then I should see "Test invalid CSV"
        When I wait for 5 seconds
        And I click the link with text that contains "Test invalid CSV"
        Then I should see "Validation status"
        And I should see "failure"
        And I should not see "success"
