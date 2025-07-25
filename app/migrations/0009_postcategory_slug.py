# Generated by Django 5.0.7
from django.db import migrations, models
from django.utils.text import slugify

def generate_category_slugs(apps, schema_editor):
    """
    Generate a unique slug for each existing PostCategory instance.
    """
    PostCategory = apps.get_model('app', 'PostCategory')
    for category in PostCategory.objects.all():
        if not category.slug:
            slug = slugify(category.name)
            unique_slug = slug
            counter = 1
            # Ensure the slug is unique by appending a number if necessary
            while PostCategory.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{slug}-{counter}'
                counter += 1
            category.slug = unique_slug
            category.save()

class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_notification'),
    ]

    operations = [
        # Add the slug field, but allow it to be null temporarily.
        # This avoids the UNIQUE constraint error on existing rows.
        migrations.AddField(
            model_name='postcategory',
            name='slug',
            field=models.SlugField(max_length=100, null=True, unique=True),
        ),
        
        # Run the Python function to populate the new slug field for all existing categories.
        migrations.RunPython(generate_category_slugs, migrations.RunPython.noop),

        # Now that all slugs are populated, alter the field to make it non-nullable (blank=True is standard for slugs).
        migrations.AlterField(
            model_name='postcategory',
            name='slug',
            field=models.SlugField(blank=True, max_length=100, unique=True),
        ),
    ]
