from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

POSITIVE_INTEGER_VALIDATORS = [
    MinValueValidator(1), MaxValueValidator(2147483647),
]


class Tag(models.Model):
    name = models.CharField('Название', max_length=32, unique=True)
    slug = models.SlugField('Слаг', max_length=32, unique=True)

    class Meta:
        ordering = ('id',)
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=128, db_index=True)
    measurement_unit = models.CharField('Единица измерения', max_length=64)

    class Meta:
        ordering = ('name', 'id')
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'), name='unique_ingredient',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='recipes', verbose_name='Автор',
    )
    name = models.CharField('Название', max_length=256)
    image = models.ImageField('Изображение', upload_to='recipes/images/')
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(
        Ingredient, through='RecipeIngredient', related_name='recipes',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (мин.)', validators=POSITIVE_INTEGER_VALIDATORS,
    )
    created_at = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cooking_time__gte=1),
                name='recipe_positive_cooking_time',
            ),
        ]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        'Количество', validators=POSITIVE_INTEGER_VALIDATORS,
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=1), name='positive_amount',
            ),
        ]

    def __str__(self):
        return f'{self.recipe}: {self.ingredient} — {self.amount}'


class UserRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='%(class)s', verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='%(class)s',
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'), name='unique_%(class)s',
            ),
        ]

    def __str__(self):
        return f'{self.user}: {self.recipe}'


class Favorite(UserRecipe):
    class Meta(UserRecipe.Meta):
        abstract = False
        verbose_name = 'избранный рецепт'
        verbose_name_plural = 'Избранное'


class ShoppingCart(UserRecipe):
    class Meta(UserRecipe.Meta):
        abstract = False
        verbose_name = 'покупка'
        verbose_name_plural = 'Список покупок'
