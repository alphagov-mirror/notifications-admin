from boto3 import resource

from flask import current_app
from notifications_utils.s3 import s3upload as utils_s3upload

FILE_LOCATION_STRUCTURE = 'service-{}/{}.pdf'


def get_transient_letter_file_location(service_id, upload_id):
    return FILE_LOCATION_STRUCTURE.format(service_id, upload_id)


def upload_letter_to_s3(data, file_location, status):
    # make the argument metadata instead?
    utils_s3upload(
        filedata=data,
        region=current_app.config['AWS_REGION'],
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location=file_location,
        metadata={'status': status}
    )


def get_letter_pdf_and_metadata(file_location):
    s3 = resource('s3')
    s3_object = s3.Object(current_app.config['TRANSIENT_UPLOADED_LETTERS'], file_location).get()

    pdf = s3_object['Body'].read()
    metadata = s3_object['Metadata']

    return pdf, metadata
