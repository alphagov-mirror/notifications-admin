from flask import Blueprint

main = Blueprint('main', __name__)
no_cookie = Blueprint('no_cookie', __name__)

from app.main.views import (  # noqa isort:skip
    add_service,
    agreement,
    api_keys,
    broadcast,
    choose_account,
    code_not_received,
    conversation,
    dashboard,
    email_branding,
    feedback,
    find_services,
    find_users,
    forgot_password,
    history,
    inbound_number,
    index,
    invites,
    jobs,
    letter_branding,
    manage_users,
    new_password,
    notifications,
    organisations,
    platform_admin,
    providers,
    register,
    returned_letters,
    send,
    service_settings,
    sign_in,
    sign_out,
    styleguide,
    templates,
    two_factor,
    uploads,
    user_profile,
    verify,
)
