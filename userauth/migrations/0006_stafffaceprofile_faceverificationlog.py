import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userauth', '0005_visitor_induction_completed_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffFaceProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('face_encoding', models.JSONField(
                    help_text='128-dimension face descriptor array from face-api.js'
                )),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('staff', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='face_profile',
                    to='userauth.staffcheckinout',
                )),
            ],
            options={
                'verbose_name': 'Staff Face Profile',
                'verbose_name_plural': 'Staff Face Profiles',
            },
        ),
        migrations.CreateModel(
            name='FaceVerificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('staff_id_no', models.CharField(blank=True, max_length=50)),
                ('attempt_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('confidence_score', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=5, null=True,
                    help_text='Similarity score as percentage (0-100)'
                )),
                ('outcome', models.CharField(
                    choices=[
                        ('matched',  'Matched (>=90%)'),
                        ('warned',   'Warned (60-89%)'),
                        ('blocked',  'Blocked (<60%)'),
                        ('override', 'Security Override'),
                        ('enrolled', 'First Enrolment'),
                        ('no_face',  'No Face Detected'),
                    ],
                    default='matched', max_length=20,
                )),
                ('override_reason', models.TextField(blank=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('override_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='face_overrides',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('staff', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='face_logs',
                    to='userauth.staffcheckinout',
                )),
            ],
            options={
                'verbose_name': 'Face Verification Log',
                'verbose_name_plural': 'Face Verification Logs',
                'ordering': ['-attempt_time'],
            },
        ),
    ]
