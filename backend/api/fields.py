import base64
import binascii
from uuid import uuid4

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            if not data.startswith('data:image/') or ';base64,' not in data:
                raise serializers.ValidationError(
                    'Передайте изображение Base64.',
                )
            header, encoded = data.split(';base64,', 1)
            if len(encoded) > 7 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Размер файла превышает 5 МБ.',
                )
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                raise serializers.ValidationError('Некорректный Base64.')
            if not decoded or len(decoded) > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Допустимый размер: от 1 б до 5 МБ.',
                )
            extension = header.split('/')[-1].lower()
            if extension == 'jpeg':
                extension = 'jpg'
            data = ContentFile(decoded, name=f'{uuid4().hex}.{extension}')
        return super().to_internal_value(data)
