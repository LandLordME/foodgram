import csv
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import Ingredient, Tag


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON/CSV и базовые теги без дубликатов.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source', nargs='?',
            default=str(
                settings.BASE_DIR.parent / 'data' / 'ingredients.json',
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source = Path(options['source'])
        try:
            with source.open(encoding='utf-8-sig', newline='') as stream:
                if source.suffix.lower() == '.csv':
                    rows = list(csv.DictReader(
                        stream, fieldnames=('name', 'measurement_unit'),
                    ))
                    if rows and rows[0]['name'] == 'name':
                        rows = rows[1:]
                else:
                    rows = json.load(stream)
            ingredients = []
            for row in rows:
                ingredient = Ingredient(
                    name=row['name'].strip(),
                    measurement_unit=row['measurement_unit'].strip(),
                )
                ingredient.full_clean(validate_unique=False,
                                      validate_constraints=False)
                ingredients.append(ingredient)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CommandError(f'Не удалось прочитать {source}: {error}')
        Ingredient.objects.bulk_create(
            ingredients, ignore_conflicts=True, batch_size=500,
        )
        for name, slug in (
            ('Завтрак', 'breakfast'), ('Обед', 'lunch'), ('Ужин', 'dinner'),
        ):
            Tag.objects.get_or_create(slug=slug, defaults={'name': name})
        self.stdout.write(self.style.SUCCESS(
            f'Ингредиентов в БД: {Ingredient.objects.count()}; '
            f'тегов: {Tag.objects.count()}.',
        ))
