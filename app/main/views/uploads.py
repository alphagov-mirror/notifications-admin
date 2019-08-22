from flask import flash, redirect, render_template, request, url_for

from app import current_service
from app.extensions import antivirus_client
from app.main import main
from app.main.forms import PDFUploadForm
from app.utils import user_has_permissions

MAX_FILE_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB


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

        virus_free = antivirus_client.scan(pdf_file)
        if not virus_free:
            flash('The file you uploaded contains a virus', 'dangerous')
            return render_template('views/uploads/choose-file.html', form=form), 400

        if len(pdf_file.read()) > MAX_FILE_UPLOAD_SIZE:
            flash('File must be smaller than 2MB', 'dangerous')
            return render_template('views/uploads/choose-file.html', form=form), 400
        pdf_file.seek(0)

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
