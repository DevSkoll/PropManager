from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workorders', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='WorkOrderImage',
            new_name='WorkOrderAttachment',
        ),
        migrations.RenameField(
            model_name='workorderattachment',
            old_name='image',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='workorderattachment',
            name='file',
            field=models.FileField(upload_to='workorder_attachments/%Y/%m/'),
        ),
        migrations.AlterField(
            model_name='workorderattachment',
            name='work_order',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name='attachments',
                to='workorders.workorder',
            ),
        ),
    ]
