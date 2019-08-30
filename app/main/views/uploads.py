import base64
import uuid
from io import BytesIO

import requests
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from notifications_utils.pdf import extract_page_from_pdf, pdf_page_count
from notifications_utils.s3 import s3upload as utils_s3upload
from PyPDF2.utils import PdfReadError
from requests import RequestException

from app import notification_api_client
from app.extensions import antivirus_client
from app.main import main
from app.main.forms import PDFUploadForm
from app.s3_client.s3_logo_client import get_s3_object
from app.utils import get_template, user_has_permissions

MAX_FILE_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB
MAX_PAGE_LENGTH = 10


@main.route("/services/<service_id>/uploads")
@user_has_permissions('send_messages')
def uploads(service_id):
    return render_template('views/uploads/index.html')


@main.route("/services/<service_id>/upload-letter", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def upload_letter(service_id):
    form = PDFUploadForm()

    if form.validate_on_submit():
        pdf_file = form.file.data

        # what if antivirus raises an error / can't be connected to?
        # virus_free = antivirus_client.scan(pdf_file)
        virus_free = True

        if not virus_free:
            return invalid_upload_error_message('The file you uploaded contains a virus')

        if len(pdf_file.read()) > MAX_FILE_UPLOAD_SIZE:
            return invalid_upload_error_message('File must be smaller than 2MB')
        pdf_file.seek(0)

        try:
            page_count = pdf_page_count(pdf_file.stream)
            pdf_file.seek(0)
        except PdfReadError:
            current_app.logger.info('Invalid PDF uploaded for service_id: {}'.format(service_id))
            return invalid_upload_error_message('File must be a valid PDF')

        upload_id = uuid.uuid4()
        bucket_name, file_location = get_transient_letter_location(service_id, upload_id)

        try:
            response = sanitise_letter(pdf_file)
            response.raise_for_status()
        except RequestException as ex:
            if ex.response is not None and ex.response.status_code == 400:
                pdf_file.seek(0)
                utils_s3upload(
                    filedata=pdf_file.stream.read(),
                    region=current_app.config['AWS_REGION'],
                    bucket_name=bucket_name,
                    file_location=file_location,
                    metadata={'status': 'invalid'}
                )
            else:
                raise ex
        else:
            utils_s3upload(
                filedata=response.content,
                region=current_app.config['AWS_REGION'],
                bucket_name=bucket_name,
                file_location=file_location,
                metadata={'status': 'valid'}
            )

        return redirect(
            url_for(
                'main.uploaded_letter_preview',
                service_id=service_id,
                file_id=upload_id,
                original_filename=pdf_file.filename,
                page_count=page_count,
            )
        )

    return render_template('views/uploads/choose-file.html', form=form)


def sanitise_letter(pdf_file):
    return requests.post(
        '{}/precompiled/sanitise'.format(current_app.config['TEMPLATE_PREVIEW_API_HOST']),
        data=pdf_file,
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )


# move to an S3 helper file
def get_transient_letter_location(service_id, upload_id):
    return (
        current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        'service-{}/{}.pdf'.format(service_id, upload_id)
    )


def invalid_upload_error_message(message):
    flash(message, 'dangerous')
    return render_template('views/uploads/choose-file.html', form=PDFUploadForm()), 400


# page where we view a notification
@main.route("/services/<service_id>/preview-letter/<file_id>")
@user_has_permissions('send_messages')
def uploaded_letter_preview(service_id, file_id):
    original_filename = request.args.get('original_filename')
    page_count = request.args.get('page_count')

    template_dict = notification_api_client.get_precompiled_template(service_id)

    print('&&& page count is {} &&&&&&&'.format(page_count), end='\n\n\n')

    template = get_template(
        template_dict,
        service_id,
        letter_preview_url=url_for(
            '.view_letter_upload_as_preview',
            service_id=service_id,
            file_id=file_id
        ),
        page_count=page_count
    )

    return render_template('views/uploads/preview.html', original_filename=original_filename, template=template)


# this is the page that makes the image
@main.route("/services/<service_id>/preview-letter-image/<file_id>")
@user_has_permissions('send_messages')
def view_letter_upload_as_preview(service_id, file_id):
    s3_object = get_s3_object(
        current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        'service-{}/{}.pdf'.format(service_id, file_id)
    )
    status = s3_object.get()['Metadata']['status']
    pdf_file = s3_object.get()['Body'].read()

    page = request.args.get('page')
    pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

    if status == 'invalid':
        path = '/precompiled/overlay.png'
        query_string = '?page_number={}'.format(page) if page else ''
        content = pdf_page
    else:
        query_string = '?hide_notify=true' if page == '1' else ''
        path = '/precompiled-preview.png'
        content = base64.b64encode(pdf_page).decode('utf-8')

    url = current_app.config['TEMPLATE_PREVIEW_API_HOST'] + path + query_string
    response_content = _get_png_preview_or_overlaid_pdf(url, content)

    display_file = base64.b64decode(response_content)

    return display_file


def _get_png_preview_or_overlaid_pdf(url, data):
    resp = requests.post(
        url,
        data=data,
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )
    # if resp.status_code != 200:
    #     raise InvalidRequest()

    return base64.b64encode(resp.content).decode('utf-8')
