import pytest
from flask import Flask

from app import create_app
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    OrgNavigation,
)
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID, normalize_spaces


def flask_app():
    app = Flask('app')
    create_app(app)

    ctx = app.app_context()
    ctx.push()

    yield app


all_endpoints = [
    rule.endpoint for rule in next(flask_app()).url_map.iter_rules()
]

navigation_instances = (
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
    CaseworkNavigation(),
)


@pytest.mark.parametrize('navigation_instance', navigation_instances)
def test_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_with_navigation:
        assert (
            endpoint in all_endpoints
        ), '{} is not a real endpoint (in {}.mapping)'.format(
            endpoint,
            type(navigation_instance).__name__
        )
        assert (
            endpoint not in navigation_instance.endpoints_without_navigation
        ), '{} is listed in {}.mapping and {}.exclude'.format(
            endpoint,
            type(navigation_instance).__name__,
            type(navigation_instance).__name__,
        )
        assert (
            navigation_instance.endpoints_with_navigation.count(endpoint) == 1
        ), '{} found more than once in {}.mapping'.format(
            endpoint,
            type(navigation_instance).__name__
        )


@pytest.mark.parametrize('navigation_instance', navigation_instances)
def test_excluded_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_without_navigation:
        assert (
            endpoint in all_endpoints
        ), '{} is not a real endpoint (in {}.exclude)'.format(
            endpoint,
            type(navigation_instance).__name__
        )
        assert (
            endpoint not in navigation_instance.endpoints_with_navigation
        ), '{} is listed in {}.exclude and {}.mapping'.format(
            endpoint,
            type(navigation_instance).__name__,
            type(navigation_instance).__name__,
        )
        assert (
            navigation_instance.endpoints_without_navigation.count(endpoint) == 1
        ), '{} found more than once in {}.exclude'.format(
            endpoint,
            type(navigation_instance).__name__
        )


@pytest.mark.parametrize('navigation_instance', navigation_instances)
def test_all_endpoints_are_covered(navigation_instance):
    for endpoint in all_endpoints:
        if not endpoint == 'main.monthly_billing_usage':
            assert endpoint in (
                navigation_instance.endpoints_with_navigation +
                navigation_instance.endpoints_without_navigation
            ), '{} is not listed or excluded in {}'.format(
                endpoint,
                type(navigation_instance).__name__
            )


@pytest.mark.parametrize('navigation_instance', navigation_instances)
@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(
    client_request, navigation_instance
):
    navigation_instance.is_selected('foo')


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.choose_template', 'Templates'),
    ('main.manage_users', 'Team members'),
])
def test_a_page_should_nave_selected_navigation_item(
    client_request,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.documentation', 'Documentation'),
    ('main.support', 'Support'),
])
def test_a_page_should_nave_selected_header_navigation_item(
    client_request,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select('.govuk-header__navigation-item--active')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize('endpoint, selected_nav_item', [
    ('main.organisation_dashboard', 'Usage'),
    ('main.manage_org_users', 'Team members'),
])
def test_a_page_should_nave_selected_org_navigation_item(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    endpoint,
    selected_nav_item,
    mocker
):
    mocker.patch(
        'app.organisations_client.get_services_and_usage', return_value={'services': {}}
    )
    page = client_request.get(endpoint, org_id=ORGANISATION_ID)
    selected_nav_items = page.select('.navigation a.selected')
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


def test_navigation_urls(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
):
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert [
        a['href'] for a in page.select('.navigation a')
    ] == [
        '/services/{}'.format(SERVICE_ONE_ID),
        '/services/{}/templates'.format(SERVICE_ONE_ID),
        '/services/{}/uploads'.format(SERVICE_ONE_ID),
        '/services/{}/users'.format(SERVICE_ONE_ID),
        '/services/{}/usage'.format(SERVICE_ONE_ID),
        '/services/{}/service-settings'.format(SERVICE_ONE_ID),
        '/services/{}/api'.format(SERVICE_ONE_ID),
    ]


def test_navigation_for_services_with_broadcast_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert [
        a['href'] for a in page.select('.navigation a')
    ] == [
        '/services/{}/current-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/previous-alerts'.format(SERVICE_ONE_ID),
        '/services/{}/templates'.format(SERVICE_ONE_ID),
        '/services/{}/users'.format(SERVICE_ONE_ID),
        '/services/{}/service-settings'.format(SERVICE_ONE_ID),
    ]


def test_caseworkers_get_caseworking_navigation(
    client_request,
    mocker,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_has_no_jobs,
    active_caseworking_user,
):
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=active_caseworking_user
    )
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one('header + .govuk-width-container nav').text) == (
        'Templates Sent messages Uploads Team members'
    )


def test_caseworkers_see_jobs_nav_if_jobs_exist(
    client_request,
    mocker,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_has_jobs,
    active_caseworking_user,
):
    mocker.patch(
        'app.user_api_client.get_user',
        return_value=active_caseworking_user
    )
    page = client_request.get('main.choose_template', service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select_one('header + .govuk-width-container nav').text) == (
        'Templates Sent messages Uploads Team members'
    )
