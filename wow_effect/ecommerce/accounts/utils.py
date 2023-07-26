import os
import binascii

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail.message import EmailMultiAlternatives


redis = settings.REDIS


def _generate_code():
    return binascii.hexlify(os.urandom(20)).decode("utf-8")


def send_multi_format_email(template_prefix, template_context, target_email):
    subject_file = "graphql/accounts/%s_subject.txt" % template_prefix
    txt_file = "graphql/accounts/%s.txt" % template_prefix
    html_file = "graphql/accounts/%s.html" % template_prefix

    subject = render_to_string(subject_file).strip()
    from_email = settings.EMAIL_HOST_USER
    to = target_email
    text_content = render_to_string(txt_file, template_context)
    html_content = render_to_string(html_file, template_context)
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def token_add_to_redis(id, mode):
    token = _generate_code()
    name = f"{id}_{mode.lower()}"
    print(token)
    print(id)
    redis.set(name=name, value=token, ex=14400)
    return token


def token_delete_to_redis(id, mode):
    name = f"{id}_{mode.lower()}"
    redis.delete(name)


def get_from_redis(id, mode):
    name = f"{id}_{mode.lower()}"
    return redis.get(name=name)


def send_register_email(id, email, username, first_name, last_name):
    token_delete_to_redis(id, "register")
    token = token_add_to_redis(id, "register")
    ctxt = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "url_verify": f"{settings.CORS_ALLOWED_ORIGINS[0]}/account/email-verify/?token={token}&?email={email}",
        "btn_name": "Verify your verify . Click Me !",
    }
    print(ctxt)
    send_multi_format_email("signup_email", ctxt, target_email=email)


def send_reset_password_email(id, email, username, first_name, last_name):
    token_delete_to_redis(id, "reset_password")
    token = token_add_to_redis(id, "reset_password")
    ctxt = {
        "email": email,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "url_verify": f"{settings.CORS_ALLOWED_ORIGINS[0]}/verify-password/?token={token}&?email={email}",
        # "token": token_add_to_redis(id, "reset_password"),
        "btn_name": "Reset password . Click Me !",
    }
    send_multi_format_email("signup_email", ctxt, target_email=email)


def send_change_email(id, email, username, first_name, last_name):
    token_delete_to_redis(id, "change_email")
    token = token_add_to_redis(id, "change_email")
    ctxt = {
        "email": email,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "url_verify": f"{settings.CORS_ALLOWED_ORIGINS[0]}/account/change-email-verify/?token={token}&?email={email}",
        # "token": token_add_to_redis(id, "change_email"),
        "btn_name": "Change email . Click Me !",
    }
    send_multi_format_email("signup_email", ctxt, target_email=email)
