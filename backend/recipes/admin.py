from django.contrib import admin
from django.db.models import Count

from .models import Favorite, Ingredient, Recipe, RecipeIngredient
from .models import ShoppingCart, Tag


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ('ingredient',)
    min_num = 1
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time', 'favorite_count')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags', 'created_at')
    readonly_fields = ('favorite_count', 'created_at')
    autocomplete_fields = ('author',)
    filter_horizontal = ('tags',)
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').annotate(
            favorites_total=Count('favorite'),
        )

    @admin.display(description='В избранном', ordering='favorites_total')
    def favorite_count(self, obj):
        return obj.favorites_total


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    autocomplete_fields = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(Favorite, ShoppingCart)
class UserRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    autocomplete_fields = ('user', 'recipe')
