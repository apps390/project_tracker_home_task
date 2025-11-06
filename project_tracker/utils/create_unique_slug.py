
from django.utils.text import slugify
import random
import string

def generate_secure_slug(instance, field_name: str, slug_field: str = 'slug', length: int = 6):
    """
    Generate a unique, readable but secure slug.
    Combines slugified name/title + random short suffix.
    """
    base_value = getattr(instance, field_name)
    base_slug = slugify(base_value)
    
    # Generate a short random suffix (6 chars)
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    slug = f"{base_slug}-{suffix}"

    ModelClass = instance.__class__
    while ModelClass.objects.filter(**{slug_field: slug}).exists():
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        slug = f"{base_slug}-{suffix}"

    return slug
