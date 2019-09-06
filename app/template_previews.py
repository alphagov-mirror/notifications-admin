import base64
from io import BytesIO

import requests
from flask import current_app, json
from notifications_utils.pdf import extract_page_from_pdf

from app import current_service


class TemplatePreview:
    @classmethod
    def from_database_object(cls, template, filetype, values=None, page=None):
        data = {
            'letter_contact_block': template.get('reply_to_text', ''),
            'template': template,
            'values': values,
            'filename': current_service.letter_branding and current_service.letter_branding['filename']
        }
        resp = requests.post(
            '{}/preview.{}{}'.format(
                current_app.config['TEMPLATE_PREVIEW_API_HOST'],
                filetype,
                '?page={}'.format(page) if page else '',
            ),
            json=data,
            headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
        )
        return (resp.content, resp.status_code, resp.headers.items())

    @classmethod
    def from_valid_pdf_file(cls, pdf_file, page):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = requests.post(
            '{}/precompiled-preview.png{}'.format(
                current_app.config['TEMPLATE_PREVIEW_API_HOST'],
                '?hide_notify=true' if page == '1' else ''
            ),
            data=base64.b64encode(pdf_page).decode('utf-8'),
            headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
        )

        response_content = base64.b64encode(response.content).decode('utf-8')
        display_file = base64.b64decode(response_content)

        return (display_file, response.status_code, response.headers.items())

    @classmethod
    def from_invalid_pdf_file(cls, pdf_file, page):
        pdf_page = extract_page_from_pdf(BytesIO(pdf_file), int(page) - 1)

        response = requests.post(
            '{}/precompiled/overlay.png{}'.format(
                current_app.config['TEMPLATE_PREVIEW_API_HOST'],
                '?page_number={}'.format(page) if page else ''
            ),
            data=pdf_page,
            headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
        )

        response_content = base64.b64encode(response.content).decode('utf-8')
        display_file = base64.b64decode(response_content)

        return (display_file, response.status_code, response.headers.items())

    @classmethod
    def from_example_template(cls, template, filename):
        data = {
            'letter_contact_block': template.get('reply_to_text'),
            'template': template,
            'values': None,
            'filename': filename
        }
        resp = requests.post(
            '{}/preview.png'.format(current_app.config['TEMPLATE_PREVIEW_API_HOST']),
            json=data,
            headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
        )
        return (resp.content, resp.status_code, resp.headers.items())

    @classmethod
    def from_utils_template(cls, template, filetype, page=None):
        return cls.from_database_object(
            template._template,
            filetype,
            template.values,
            page=page,
        )


def get_page_count_for_letter(template, values=None):

    if template['template_type'] != 'letter':
        return None

    page_count, _, _ = TemplatePreview.from_database_object(template, 'json', values)
    page_count = json.loads(page_count.decode('utf-8'))['count']

    return page_count


def validate_letter(pdf_file):
    return requests.post(
        '{}/precompiled/validate?include_preview=true'.format(current_app.config['TEMPLATE_PREVIEW_API_HOST']),
        data=pdf_file,
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )


def sanitise_letter(pdf_file):
    return requests.post(
        '{}/precompiled/sanitise'.format(current_app.config['TEMPLATE_PREVIEW_API_HOST']),
        data=pdf_file,
        headers={'Authorization': 'Token {}'.format(current_app.config['TEMPLATE_PREVIEW_API_KEY'])}
    )
