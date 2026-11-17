import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import User


class Command(BaseCommand):
    help = 'Создаёт демонстрационных пользователей и по рецепту для каждого.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=os.getenv('DEMO_PASSWORD'))

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        if not password:
            raise CommandError(
                'Укажите --password или переменную DEMO_PASSWORD.',
            )
        call_command('import_ingredients')
        ingredient = Ingredient.objects.get_or_create(
            name='овсяные хлопья', measurement_unit='г',
        )[0]
        for index, (username, title, color) in enumerate((
            ('chef_anna', 'Овсяная каша с ягодами', '#a53448'),
            ('chef_ivan', 'Домашняя овсяная гранола', '#b98b3b'),
            ('demo_admin', 'Овсяное печенье к завтраку', '#6b8e42'),
        )):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': ('Анна', 'Иван', 'Администратор')[index],
                    'last_name': 'Демонстрационный',
                    'is_staff': index == 2, 'is_superuser': index == 2,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            if Recipe.objects.filter(author=user, name=title).exists():
                continue
            image = Image.new('RGB', (640, 480), '#f3ede2')
            draw = ImageDraw.Draw(image)
            draw.ellipse((140, 60, 500, 420), fill='white', outline='#ddd6ca',
                         width=8)
            draw.ellipse((175, 95, 465, 385), fill=color)
            for x, y in ((240, 180), (330, 260), (380, 170), (260, 310)):
                draw.ellipse((x, y, x + 25, y + 25), fill='#f0d2a5')
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            recipe = Recipe(
                author=user, name=title, cooking_time=15 + index * 5,
                text=('Смешайте ингредиенты. Приготовьте до готовности '
                      'и подавайте к столу. Это демонстрационный рецепт '
                      'для проверки сервиса.'),
            )
            recipe.image.save(
                f'{username}.png', ContentFile(buffer.getvalue()), save=False,
            )
            recipe.save()
            recipe.tags.add(Tag.objects.get(slug='breakfast'))
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, amount=100 + index * 50,
            )
        self.stdout.write(self.style.SUCCESS(
            'Данные готовы. Аккаунты: chef_anna, chef_ivan, demo_admin '
            '(email: <имя>@example.com). Пароль задан вами.',
        ))
