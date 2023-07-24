from behave import when, then
from behaving.personas.steps import *  # noqa: F401, F403
from behaving.web.steps import *  # noqa: F401, F403
from behaving.web.steps.basic import should_see


@when(u'I take a debugging screenshot')
def debug_screenshot(context):
    """ Take a screenshot only if debugging is enabled in the persona.
    """
    if context.persona and context.persona.get('debug') == 'True':
        context.execute_steps(u"""
            Then I take a screenshot
        """)


@when(u'I go to homepage')
def go_to_home(context):
    context.execute_steps(u"""
        When I visit "/"
    """)


@then(u'I should see text containing quotes `{text}`')
def should_see_backquoted(context, text):
    should_see(context, text)


@when(u'I go to register page')
def go_to_register_page(context):
    context.execute_steps(u"""
        When I go to homepage
        And I press "Register"
    """)


@when(u'I log in')
def log_in(context):
    context.execute_steps(u"""
        When I go to homepage
        And I expand the browser height
        And I press "Log in"
        And I log in directly
    """)


@when(u'I expand the browser height')
def expand_height(context):
    # Work around x=null bug in Selenium set_window_size
    context.browser.driver.set_window_rect(x=0, y=0, width=1024, height=4096)


@when(u'I log in directly')
def log_in_directly(context):
    """
    This differs to the `log_in` function above by logging in directly to a page where the user login form is presented
    :param context:
    :return:
    """

    assert context.persona, "A persona is required to log in, found [{}] in context. Have you configured the personas in before_scenario?".format(context.persona)
    context.execute_steps(u"""
        When I attempt to log in with password "$password"
        Then I should see an element with xpath "//a[@title='Log out']"
    """)


@when(u'I attempt to log in with password "{password}"')
def attempt_login(context, password):
    assert context.persona
    context.execute_steps(u"""
        When I fill in "login" with "$name"
        And I fill in "password" with "{}"
        And I press the element with xpath "//button[contains(string(), 'Login')]"
    """.format(password))


@when(u'I open the new resource form for dataset "{name}"')
def go_to_new_resource_form(context, name):
    context.execute_steps(u"""
        When I edit the "{0}" dataset
    """.format(name))
    if context.browser.is_element_present_by_xpath("//*[contains(@class, 'btn-primary') and contains(string(), 'Next:')]"):
        # Draft dataset, proceed directly to resource form
        context.execute_steps(u"""
            When I press "Next:"
        """)
    else:
        # Existing dataset, browse to the resource form
        context.execute_steps(u"""
            When I press "Resources"
            And I press "Add new resource"
        """)


@when(u'I create a resource with name "{name}" and URL "{url}"')
def add_resource(context, name, url):
    context.execute_steps(u"""
        When I log in
        And I open the new resource form for dataset "warandpeace"
        And I execute the script "$('#resource-edit [name=url]').val('{url}')"
        And I fill in "name" with "{name}"
        And I fill in "description" with "description"
        And I execute the script "document.getElementById('field-format').value='HTML'"
        And I press the element with xpath "//form[contains(@class, 'resource-form')]//button[contains(@class, 'btn-primary')]"
    """.format(name=name, url=url))


@when(u'I go to dataset page')
def go_to_dataset_page(context):
    context.execute_steps(u"""
        When I visit "/dataset"
    """)


@when(u'I go to dataset "{name}"')
def go_to_dataset(context, name):
    context.execute_steps(u"""
        When I visit "/dataset/{0}"
    """.format(name))


@when(u'I edit the "{name}" dataset')
def edit_dataset(context, name):
    context.execute_steps(u"""
        When I go to dataset "{0}"
        And I click the link with text that contains "Manage"
    """.format(name))


@when(u'I go to organisation page')
def go_to_organisation_page(context):
    context.execute_steps(u"""
        When I visit "/organization"
    """)


@when(u'I search the autocomplete API for user "{username}"')
def go_to_user_autocomplete(context, username):
    context.execute_steps(u"""
        When I visit "/api/2/util/user/autocomplete?q={0}"
    """.format(username))


@when(u'I go to the user list API')
def go_to_user_list(context):
    context.execute_steps(u"""
        When I visit "/api/3/action/user_list"
    """)


@when(u'I go to the "{user_id}" profile page')
def go_to_user_profile(context, user_id):
    context.execute_steps(u"""
        When I visit "/user/{0}"
    """.format(user_id))


@when(u'I go to the dashboard')
def go_to_dashboard(context):
    context.execute_steps(u"""
        When I visit "/dashboard/datasets"
    """)


@then(u'I should see my datasets')
def dashboard_datasets(context):
    context.execute_steps(u"""
        Then I should see an element with xpath "//li[contains(@class, 'active') and contains(string(), 'My Datasets')]"
    """)


@when(u'I go to the "{user_id}" user API')
def go_to_user_show(context, user_id):
    context.execute_steps(u"""
        When I visit "/api/3/action/user_show?id={0}"
    """.format(user_id))


@when(u'I view the "{group_id}" {group_type} API "{including}" users')
def go_to_group_including_users(context, group_id, group_type, including):
    if group_type == "organisation":
        group_type = "organization"
    context.execute_steps(u"""
        When I visit "/api/3/action/{1}_show?id={0}&include_users={2}"
    """.format(group_id, group_type, including in ['with', 'including']))


# ckanext-validation


@then(u'I should see a validation timestamp')
def should_see_validation_timestamp(context):
    context.execute_steps(u"""
        Then I should see "Validation timestamp"
        And I should see an element with xpath "//th[contains(string(), 'Validation timestamp')]/../td[contains(string(), '-') and contains(string(), ':') and contains(string(), '.')]"
    """)
