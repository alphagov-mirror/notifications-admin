from flask import redirect, render_template, request, url_for

from app import current_service
from app.main import main
from app.main.forms import PDFUploadForm
from app.utils import user_has_permissions


@main.route("/services/<service_id>/uploads")
@user_has_permissions('send_messages')
def uploads(service_id):
    return render_template('views/uploads/index.html')


@main.route("/services/<service_id>/uploads/choose-file", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def choose_upload_file(service_id):
    form = PDFUploadForm()

    if form.validate_on_submit():
        pdf_file = form.file.data

        return redirect(
            url_for(
                'main.upload_letter_preview',
                service_id=current_service.id,
                filename=pdf_file.filename,
            )
        )

    return render_template('views/uploads/choose-file.html', form=form)


@main.route("/services/<service_id>/uploads/preview")
@user_has_permissions('send_messages')
def upload_letter_preview(service_id):
    filename = request.args.get('filename')

    return render_template('views/uploads/preview.html', filename=filename)
