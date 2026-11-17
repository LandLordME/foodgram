from django_filters import rest_framework as filters

from recipes.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug', to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.ChoiceFilter(
        choices=(('0', 'Нет'), ('1', 'Да')), method='filter_favorited',
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=(('0', 'Нет'), ('1', 'Да')), method='filter_shopping_cart',
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')

    def filter_favorited(self, queryset, name, value):
        return queryset.filter(is_favorited=value == '1')

    def filter_shopping_cart(self, queryset, name, value):
        return queryset.filter(is_in_shopping_cart=value == '1')
