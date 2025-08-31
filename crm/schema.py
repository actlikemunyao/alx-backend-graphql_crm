import graphene
from crm.models import Product

class ProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    stock = graphene.Int()

class UpdateLowStockProducts(graphene.Mutation):
    success = graphene.Boolean()
    updated_products = graphene.List(ProductType)

    def mutate(self, info):
        products = Product.objects.filter(stock__lt=10)
        updated = []
        for product in products:
            product.stock += 10
            product.save()
            updated.append(product)
        return UpdateLowStockProducts(success=True, updated_products=updated)

class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()

class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, world!")

schema = graphene.Schema(query=Query, mutation=Mutation)
