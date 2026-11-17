import base64
import tempfile
from io import BytesIO

from django.core.files.base import ContentFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from recipes.models import Ingredient, Recipe, RecipeIngredient, ShoppingCart
from recipes.models import Tag
from users.models import User


class FoodgramScenariosTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = tempfile.TemporaryDirectory()
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        cls.media.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.author = User.objects.create_user(
            username='author', email='author@example.com',
            password='TestPass!42',
            first_name='Анна', last_name='Повар',
        )
        self.reader = User.objects.create_user(
            username='reader', email='reader@example.com',
            password='TestPass!42',
            first_name='Иван', last_name='Читатель',
        )
        self.sugar = Ingredient.objects.create(
            name='Сахар', measurement_unit='г')
        self.tag = Tag.objects.create(name='Завтрак', slug='breakfast')
        buffer = BytesIO()
        Image.new('RGB', (8, 8), 'green').save(buffer, 'PNG')
        self.image = buffer.getvalue()
        self.recipe = self.make_recipe('Каша', self.sugar, 100)

    def make_recipe(self, name, ingredient, amount):
        recipe = Recipe.objects.create(
            author=self.author, name=name, text='Приготовьте блюдо.',
            cooking_time=10, image=ContentFile(self.image, name=f'{name}.png'),
        )
        recipe.tags.add(self.tag)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=ingredient, amount=amount,
        )
        return recipe

    def payload(self):
        return {
            'name': 'Новый рецепт', 'text': 'Описание', 'cooking_time': 20,
            'ingredients': [{'id': self.sugar.pk, 'amount': 150}],
            'tags': [self.tag.pk],
        }

    def test_shopping_list_sums_and_separates_units_and_users(self):
        second = self.make_recipe('Пирог', self.sugar, 50)
        spoons = Ingredient.objects.create(
            name='Сахар', measurement_unit='ложка')
        third = self.make_recipe('Чай', spoons, 2)
        other = self.make_recipe('Чужой список', self.sugar, 999)
        for recipe in (self.recipe, second, third):
            ShoppingCart.objects.create(user=self.reader, recipe=recipe)
        ShoppingCart.objects.create(user=self.author, recipe=other)
        self.client.force_authenticate(self.reader)
        response = self.client.get('/api/recipes/download_shopping_cart/')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode('utf-8')
        self.assertIn('Сахар (г) — 150', text)
        self.assertIn('Сахар (ложка) — 2', text)
        self.assertEqual(text.count('Сахар (г)'), 1)
        self.assertNotIn('999', text)

    def test_reader_cannot_edit_recipe_but_can_save_it_privately(self):
        self.client.force_authenticate(self.reader)
        url = f'/api/recipes/{self.recipe.pk}/'
        response = self.client.patch(url, self.payload(), 'json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post(url + 'favorite/').status_code, 201)
        self.assertEqual(self.client.post(url + 'favorite/').status_code, 400)
        self.assertTrue(self.client.get(url).data['is_favorited'])
        self.client.force_authenticate(self.author)
        self.assertFalse(self.client.get(url).data['is_favorited'])
        self.assertEqual(self.client.get('/api/recipes/?is_favorited=1').data[
            'count'], 0)

    def test_invalid_nested_update_leaves_original_recipe_untouched(self):
        self.client.force_authenticate(self.author)
        data = self.payload()
        data['ingredients'] *= 2
        response = self.client.patch(
            f'/api/recipes/{self.recipe.pk}/', data, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, 'Каша')
        self.assertEqual(self.recipe.recipe_ingredients.get().amount, 100)

    def test_short_link_stays_stable_after_edit_and_resolves_for_guest(self):
        endpoint = f'/api/recipes/{self.recipe.pk}/get-link/'
        before = self.client.get(endpoint).data['short-link']
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.patch(
            f'/api/recipes/{self.recipe.pk}/', self.payload(), format='json',
        ).status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(endpoint).data['short-link'], before)
        response = self.client.get(before)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'/recipes/{self.recipe.pk}')

    def test_ingredient_search_matches_cyrillic_prefix_in_any_case(self):
        Ingredient.objects.create(name='Сахарная пудра', measurement_unit='г')
        Ingredient.objects.create(
            name='Тростниковый сахар', measurement_unit='г')
        response = self.client.get('/api/ingredients/', {'name': 'сАХаР'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item['name'] for item in response.data},
                         {'Сахар', 'Сахарная пудра'})

    def test_private_subscriptions_with_recipe_limit_and_total(self):
        newest = self.make_recipe('Новый завтрак', self.sugar, 70)
        self.client.force_authenticate(self.reader)
        url = f'/api/users/{self.author.pk}/subscribe/?recipes_limit=1'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['recipes_count'], 2)
        self.assertEqual([item['id'] for item in response.data['recipes']],
                         [newest.pk])
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(self.client.post(
            f'/api/users/{self.reader.pk}/subscribe/',
        ).status_code, 400)
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.get('/api/users/subscriptions/').data[
            'count'], 0)
        self.client.force_authenticate(None)
        response = self.client.get('/api/users/subscriptions/')
        self.assertEqual(response.status_code, 401)

    def test_registration_login_and_base64_avatar_lifecycle(self):
        response = self.client.post('/api/users/', {
            'email': 'new@example.com', 'username': 'new_user',
            'first_name': 'Новый', 'last_name': 'Повар',
            'password': 'Secure-test-Pass!274',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        token = self.client.post('/api/auth/token/login/', {
            'email': 'new@example.com', 'password': 'Secure-test-Pass!274',
        }, format='json')
        self.assertEqual(token.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Token '
                                + token.data['auth_token'])
        image = 'data:image/png;base64,' + \
            base64.b64encode(self.image).decode()
        response = self.client.put('/api/users/me/avatar/',
                                   {'avatar': image}, 'json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.get('/api/users/me/').data['avatar'])
        response = self.client.delete('/api/users/me/avatar/')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.client.get('/api/users/me/').data['avatar'])
        response = self.client.post('/api/auth/token/logout/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get('/api/users/me/').status_code, 401)
