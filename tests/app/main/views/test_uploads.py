from flask import url_for

from app.utils import normalize_spaces
from tests.conftest import SERVICE_ONE_ID


def test_get_upload_hub_page(client_request):
    page = client_request.get('main.uploads', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Uploads'
    assert page.find('a', text='Upload a letter').attrs['href'] == url_for(
        'main.choose_upload_file', service_id=SERVICE_ONE_ID
    )


def test_get_choose_upload_file(client_request):
    page = client_request.get('main.choose_upload_file', service_id=SERVICE_ONE_ID)

    assert page.find('h1').text == 'Upload a letter'
    assert page.find('input', class_='file-upload-field')
    assert page.select('button[type=submit]')


def test_post_choose_upload_file_redirects_for_valid_file(mocker, client_request):
    antivirus_mock = mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        client_request.post(
            'main.choose_upload_file',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_redirect=url_for(
                'main.upload_letter_preview',
                service_id=SERVICE_ONE_ID,
                filename='tests/test_pdf_files/one_page_pdf.pdf',
                _external=True
            )
        )
        assert antivirus_mock.called


def test_post_choose_upload_file_shows_error_when_file_is_not_a_pdf(mocker, client_request):
    antivirus_mock = mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=True)

    with open('tests/non_spreadsheet_files/actually_a_png.csv', 'rb') as file:
        page = client_request.post(
            'main.choose_upload_file',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=200
        )
    assert page.find('span', class_='error-message').text.strip() == "Your file must be a PDF"
    assert not antivirus_mock.called


def test_post_choose_upload_file_shows_error_when_no_file_uploaded(client_request):
    page = client_request.post(
        'main.choose_upload_file',
        service_id=SERVICE_ONE_ID,
        _data={'file': ''},
        _expected_status=200
    )
    assert page.find('span', class_='error-message').text.strip() == "You need to upload a file to submit"


def test_post_choose_upload_file_when_file_contains_virus(mocker, client_request):
    mocker.patch('app.main.views.uploads.antivirus_client.scan', return_value=False)

    with open('tests/test_pdf_files/one_page_pdf.pdf', 'rb') as file:
        page = client_request.post(
            'main.choose_upload_file',
            service_id=SERVICE_ONE_ID,
            _data={'file': file},
            _expected_status=400
        )
    assert page.find('h1').text == 'Upload a letter'
    assert normalize_spaces(page.select('.banner-dangerous')[0].text) == 'The file you uploaded contains a virus'


def test_upload_letter_preview(client_request):
    page = client_request.get('main.upload_letter_preview', service_id=SERVICE_ONE_ID, filename='my_letter.pdf')

    assert page.find('h1').text == 'my_letter.pdf'
