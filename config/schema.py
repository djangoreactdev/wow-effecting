import graphene
from graphql_jwt import mutations
from wow_effect.ecommerce.product.queries import ProductQuery
from wow_effect.ecommerce.comment.mutations import CommentMutation
from wow_effect.ecommerce.accounts.mutations import AccountsMutation
from wow_effect.ecommerce.accounts.queries import AccountsQuery
from wow_effect.ecommerce.category.queries import CategoryQuery
from wow_effect.ecommerce.cart.queris import CartQuery
from wow_effect.ecommerce.cart.mutations import CartMutation
from wow_effect.ecommerce.order.queries import OrderQuery
from wow_effect.ecommerce.order.mutations import OrderMutations
from wow_effect.ecommerce.search.queries import SearchQuery
from wow_effect.ecommerce.blog.querice import ArticleQuery


class Query(
    ArticleQuery, SearchQuery, OrderQuery, CartQuery, CategoryQuery, AccountsQuery, ProductQuery, graphene.ObjectType
):
    pass


class Mutation(OrderMutations, CartMutation, CommentMutation, AccountsMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
