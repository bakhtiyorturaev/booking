# Generated manually to preserve existing empty columns while changing their API semantics.

import apps.clubs.models
from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0008_remove_branchimage_alt_text_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="club",
            old_name="logo_url",
            new_name="logo",
        ),
        migrations.RenameField(
            model_name="club",
            old_name="cover_url",
            new_name="cover",
        ),
        migrations.RenameField(
            model_name="branchimage",
            old_name="image_url",
            new_name="image",
        ),
        migrations.AlterField(
            model_name="club",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Klub logotipi.",
                upload_to=apps.clubs.models.club_logo_upload_to,
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp"),
                        code="3018",
                        message="3018",
                    ),
                    apps.clubs.models.validate_image_size,
                ],
            ),
        ),
        migrations.AlterField(
            model_name="club",
            name="cover",
            field=models.ImageField(
                blank=True,
                help_text="Klub muqova rasmi.",
                upload_to=apps.clubs.models.club_cover_upload_to,
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp"),
                        code="3018",
                        message="3018",
                    ),
                    apps.clubs.models.validate_image_size,
                ],
            ),
        ),
        migrations.AlterField(
            model_name="branchimage",
            name="image",
            field=models.ImageField(
                help_text="Filial rasmi.",
                upload_to=apps.clubs.models.branch_image_upload_to,
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp"),
                        code="3018",
                        message="3018",
                    ),
                    apps.clubs.models.validate_image_size,
                ],
            ),
        ),
    ]
