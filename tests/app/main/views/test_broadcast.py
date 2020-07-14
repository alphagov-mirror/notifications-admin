import json

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import sample_uuid
from tests.conftest import SERVICE_ONE_ID, normalize_spaces

sample_uuid = sample_uuid()


@pytest.mark.parametrize('endpoint, extra_args', (
    ('.broadcast_dashboard', {}),
    ('.broadcast_dashboard_updates', {}),
    ('.broadcast', {'template_id': sample_uuid}),
    ('.preview_broadcast_areas', {'broadcast_message_id': sample_uuid}),
    ('.choose_broadcast_library', {'broadcast_message_id': sample_uuid}),
    ('.choose_broadcast_area', {'broadcast_message_id': sample_uuid, 'library_slug': 'countries'}),
    ('.remove_broadcast_area', {'broadcast_message_id': sample_uuid, 'area_slug': 'england'}),
    ('.preview_broadcast_message', {'broadcast_message_id': sample_uuid}),
))
def test_broadcast_pages_403_without_permission(
    client_request,
    endpoint,
    extra_args,
):
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        **extra_args
    )


def test_dashboard_redirects_to_broadcast_dashboard(
    client_request,
    service_one,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.service_dashboard',
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            '.broadcast_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    ),


def test_empty_broadcast_dashboard(
    client_request,
    service_one,
    mock_get_no_broadcast_messages,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.broadcast_dashboard',
        service_id=SERVICE_ONE_ID,
    )
    assert [
        normalize_spaces(row.text) for row in page.select('tbody tr .table-empty-message')
    ] == [
        'You do not have any live broadcasts at the moment',
        'You do not have any previous broadcasts',
    ]


@freeze_time('2020-02-20 02:20')
def test_broadcast_dashboard(
    client_request,
    service_one,
    mock_get_broadcast_messages,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.broadcast_dashboard',
        service_id=SERVICE_ONE_ID,
    )
    assert [
        normalize_spaces(row.text) for row in page.select('table')[0].select('tbody tr')
    ] == [
        'Example template To England and Scotland Live until tomorrow at 2:20am Stop broadcasting',
    ]
    assert [
        normalize_spaces(row.text) for row in page.select('table')[1].select('tbody tr')
    ] == [
        'Example template To England and Scotland Stopped 10 February at 2:20am',
        'Example template To England and Scotland Finished yesterday at 8:20pm',
    ]


@freeze_time('2020-02-20 02:20')
def test_broadcast_dashboard_json(
    logged_in_client,
    service_one,
    mock_get_broadcast_messages,
):
    service_one['permissions'] += ['broadcast']
    response = logged_in_client.get(url_for(
        '.broadcast_dashboard_updates',
        service_id=SERVICE_ONE_ID,
    ))

    assert response.status_code == 200

    json_response = json.loads(response.get_data(as_text=True))

    assert json_response.keys() == {'live_broadcasts', 'previous_broadcasts'}

    assert 'Live until tomorrow at 2:20am' in json_response['live_broadcasts']
    assert 'Finished yesterday at 8:20pm' in json_response['previous_broadcasts']


def test_broadcast_page(
    client_request,
    service_one,
    fake_uuid,
    mock_create_broadcast_message,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.broadcast',
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    ),


def test_preview_broadcast_areas_page(
    client_request,
    service_one,
    fake_uuid,
    mock_get_draft_broadcast_message,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.preview_broadcast_areas',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


def test_choose_broadcast_library_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    page = client_request.get(
        '.choose_broadcast_library',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )
    assert [
        (normalize_spaces(title.text), normalize_spaces(hint.text))
        for title, hint in list(zip(
            page.select('.file-list-filename-large'), page.select('.file-list-hint-large')
        ))
    ] == [
        (
            'Counties and Unitary Authorities in England and Wales',
            'Barking and Dagenham, Barnet, Barnsley and 171 more…',
        ),
        (
            'Countries',
            'England, Northern Ireland, Scotland and Wales',
        ),
        (
            'Regions of England',
            'East Midlands, East of England, London and 6 more…',
        ),
    ]
    assert page.select_one('a.file-list-filename-large.govuk-link')['href'] == url_for(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='counties-and-unitary-authorities-in-england-and-wales',
    )


def test_choose_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='countries',
    )


def test_add_broadcast_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.choose_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug='countries',
        _data={
            'areas': ['england', 'wales']
        }
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'areas': ['england', 'scotland', 'wales']
        },
    )


def test_remove_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.remove_broadcast_area',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        area_slug='england',
        _expected_redirect=url_for(
            '.preview_broadcast_areas',
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            _external=True,
        ),
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'areas': ['scotland']
        },
    )


def test_preview_broadcast_message_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_get_broadcast_template,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.preview_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    ),


@freeze_time('2020-02-02 02:02:02.222222')
def test_start_broadcasting(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_get_broadcast_template,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.post(
        '.preview_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    ),
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            'starts_at': '2020-02-02T02:02:02.222222',
            'finishes_at': '2020-02-05T02:02:02.222222',
        },
    )
    mock_update_broadcast_message_status.assert_called_once_with(
        'broadcasting',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


def test_cancel_broadcast(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
):
    service_one['permissions'] += ['broadcast']
    client_request.get(
        '.cancel_broadcast_message',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            '.broadcast_dashboard',
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    ),
    mock_update_broadcast_message_status.assert_called_once_with(
        'cancelled',
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )
