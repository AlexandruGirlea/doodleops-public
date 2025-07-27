import os
import logging

import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.utils import formataddr
from django.conf import settings
from django.template.loader import render_to_string
from email_validator import validate_email, EmailNotValidError


logger = logging.getLogger(__name__)


def send_email_via_ses(
        to_email: str,
        subject: str,
        context: dict,
        template_name: str = None,
        attachments=None,
        inline_images=None,
        from_email=None,
        files=None
):
    """
    Sends an email via AWS SES using boto3.

    :param to_email: Recipient's email address
    :param subject: Email subject
    :param context: Context to render the template with
    :param template_name: Optional. Name of the template to render (Path to the template) else html_content must be provided in the context
    :param attachments: List of file paths to attach
    :param inline_images: Dict mapping CID names to image file paths for inline
    :param from_email: Optional. From email address
    :param files: Optional. Tuples of file names and file objects. If provided, attachments and inline_images will be ignored
    """
    # Validate email addresses
    try:
        valid = validate_email(to_email)
        to_email = valid.email
    except EmailNotValidError as e:
        msg = f"Invalid recipient email address: {e}"
        logger.error(msg)
        return

    if from_email:
        try:
            valid = validate_email(from_email)
            from_email = valid.normalized
        except EmailNotValidError as e:
            raise ValueError(f"Invalid sender email address: {e}")
    else:
        from_email = f"noreply@{settings.AWS_SES_DOMAIN}"

    # Render HTML content
    if template_name:
        html_content = render_to_string(template_name, context)
    else:
        html_content = context.get('html_content', '')

    # Plain text content (optional)
    text_content = context.get('text_content',
                               'This email contains HTML content.')

    # Create a multipart/mixed parent container
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = formataddr(('DoodleOps', from_email))
    msg['To'] = to_email

    # Create a multipart/alternative child container
    msg_body = MIMEMultipart('alternative')

    # Attach the plain text and HTML versions of the email
    msg_body.attach(MIMEText(text_content, 'plain'))
    msg_body.attach(MIMEText(html_content, 'html'))

    # Attach the multipart/alternative to the parent container
    msg.attach(msg_body)

    # Attach inline images
    if inline_images and not files:
        for cid, image_path in inline_images.items():
            with open(image_path, 'rb') as img:
                img_data = img.read()
                image = MIMEImage(img_data)
                image.add_header('Content-ID', f'<{cid}>')
                image.add_header('Content-Disposition', 'inline',
                                 filename=os.path.basename(image_path))
                msg.attach(image)

    # Attach files
    if files:
        for file_name, file_obj in files:
            part = MIMEApplication(file_obj.read(), Name=file_name)
            part['Content-Disposition'] = f'attachment; filename="{file_name}"'
            msg.attach(part)
    elif attachments and not files:
        for attachment_path in attachments:
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(),
                                       Name=os.path.basename(attachment_path))
                part[
                    'Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)

    # Initialize boto3 SES client
    ses_client = boto3.client(
        'ses',
        region_name=settings.AWS_SES_REGION,
        aws_access_key_id=settings.AWS_SES_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SES_SECRET_KEY
    )

    try:
        # Send the email
        response = ses_client.send_raw_email(
            Source=from_email,
            Destinations=[to_email],
            RawMessage={
                'Data': msg.as_string(),
            }
        )
    except ClientError as e:
        # Handle AWS SES errors
        msg = f"Failed to send email via SES: {e.response['Error']['Message']}"
        logger.error(msg)
        return
    except Exception as e:
        msg = f"An error occurred: {str(e)}"
        logger.error(msg)
        return

    return response
