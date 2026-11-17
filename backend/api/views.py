import re

from django.db.models import BooleanField, Count, Exists, OuterRef, Sum, Value
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import base36_to_int, int_to_base36
from djoser.serializers import SetPasswordSerializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.models import Favorite, Ingredient, Recipe, RecipeIngredient
from recipes.models import ShoppingCart, Tag
from users.models import Subscription, User

from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import AvatarSerializer, IngredientSerializer
from .serializers import RecipeMinifiedSerializer, RecipeReadSerializer
from .serializers import RecipesLimitSerializer, RecipeWriteSerializer
from .serializers import SubscriptionSerializer, TagSerializer
from .serializers import UserCreateSerializer, UserSerializer


class SubscriptionContextMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        context['subscribed_author_ids'] = (
            set(user.following.values_list('author_id', flat=True))
            if user.is_authenticated else set()
        )
        return context


class UserViewSet(SubscriptionContextMixin, mixins.CreateModelMixin,
                  mixins.ListModelMixin, mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    lookup_value_regex = r'\d+'

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=('password',))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('put', 'delete'), url_path='me/avatar',
            permission_classes=(IsAuthenticated,))
    def avatar(self, request):
        user = request.user
        if request.method == 'DELETE':
            user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(
            user, data=request.data, context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        previous = user.avatar.name
        storage = user.avatar.storage
        serializer.save()
        if previous and previous != user.avatar.name:
            storage.delete(previous)
        return Response(serializer.data)

    def subscription_context(self):
        query = RecipesLimitSerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return {**self.get_serializer_context(), **query.validated_data}

    def subscription_authors(self):
        return User.objects.annotate(
            recipes_count=Count('recipes'),
        ).prefetch_related('recipes').order_by('id')

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        context = self.subscription_context()
        authors = self.subscription_authors().filter(
            followers__user=request.user,
        )
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(page, many=True, context=context)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, pk=None):
        author = get_object_or_404(self.subscription_authors(), pk=pk)
        if request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(
                user=request.user, author=author,
            ).delete()
            if not deleted:
                raise serializers.ValidationError('Вы не подписаны на автора.')
            return Response(status=status.HTTP_204_NO_CONTENT)
        context = self.subscription_context()
        if author == request.user:
            raise serializers.ValidationError('Нельзя подписаться на себя.')
        _, created = Subscription.objects.get_or_create(
            user=request.user, author=author,
        )
        if not created:
            raise serializers.ValidationError('Вы уже подписаны на автора.')
        context['subscribed_author_ids'].add(author.pk)
        return Response(
            SubscriptionSerializer(author, context=context).data,
            status=status.HTTP_201_CREATED,
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (AllowAny,)

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(name__iregex='^' + re.escape(name))
        return queryset


class RecipeViewSet(SubscriptionContextMixin, viewsets.ModelViewSet):
    permission_classes = (IsAuthorOrReadOnly,)
    filterset_class = RecipeFilter
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self):
        queryset = Recipe.objects.select_related('author').prefetch_related(
            'tags', 'recipe_ingredients__ingredient',
        )
        user = self.request.user
        if user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    user=user, recipe=OuterRef('pk'),
                )),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    user=user, recipe=OuterRef('pk'),
                )),
            )
        return queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField()),
        )

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def manage_recipe_list(self, request, model):
        recipe = self.get_object()
        if request.method == 'DELETE':
            deleted, _ = model.objects.filter(
                user=request.user, recipe=recipe,
            ).delete()
            if not deleted:
                raise serializers.ValidationError('Рецепта нет в списке.')
            return Response(status=status.HTTP_204_NO_CONTENT)
        _, created = model.objects.get_or_create(
            user=request.user, recipe=recipe,
        )
        if not created:
            raise serializers.ValidationError('Рецепт уже добавлен в список.')
        return Response(
            RecipeMinifiedSerializer(
                recipe, context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk=None):
        return self.manage_recipe_list(request, Favorite)

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk=None):
        return self.manage_recipe_list(request, ShoppingCart)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shoppingcart__user=request.user,
        ).values(
            'ingredient_id', 'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(total=Sum('amount')).order_by('ingredient__name')
        lines = ['Список покупок', '']
        lines.extend(
            f'{item["ingredient__name"]} '
            f'({item["ingredient__measurement_unit"]}) — {item["total"]}'
            for item in ingredients
        )
        response = HttpResponse(
            '\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8',
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping-list.txt"'
        )
        return response

    @action(detail=True, methods=('get',), url_path='get-link',
            permission_classes=(AllowAny,))
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        url = reverse('short-link', args=(int_to_base36(recipe.pk),))
        return Response({'short-link': request.build_absolute_uri(url)})


def short_link(request, code):
    try:
        pk = base36_to_int(code)
    except ValueError:
        raise Http404('Рецепт не найден.')
    if not 0 < pk <= 9223372036854775807:
        raise Http404('Рецепт не найден.')
    recipe = get_object_or_404(Recipe, pk=pk)
    return redirect(f'/recipes/{recipe.pk}')
