import logging
from typing import Union
from datetime import timedelta
from urllib.parse import urlencode, unquote

from django.core import signing
from django.utils import timezone

from common.auth import encrypt_str, decrypt_str
from app_users.models import PasswordResetToken

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_SALT = 'DoodleOps email-verification'


def generate_email_verification_token(user_pk):
	token = signing.dumps({'user_pk': user_pk}, salt=EMAIL_VERIFICATION_SALT)
	token = encrypt_str(token)
	PasswordResetToken.objects.create(user_id=user_pk, token=token)
	return urlencode({'token': token})


def verify_email_token(token, max_age=60*60*24) -> Union[int, None]:
	if not token:
		return
	try:
		expiration_time = timezone.now() - timedelta(hours=24)
		PasswordResetToken.objects.filter(created_at__lt=expiration_time).delete()

		data = signing.loads(
			decrypt_str(unquote(token)),
			salt=EMAIL_VERIFICATION_SALT,
			max_age=max_age
		)
		PasswordResetToken.objects.get(
			token=token, used=False, user_id=data['user_pk']
		)
		return data['user_pk']

	except (
			signing.SignatureExpired, signing.BadSignature,
			PasswordResetToken.DoesNotExist
	):
		pass
	except Exception as e:
		logger.error('Error verifying email verification token: %s', e)
