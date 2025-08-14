import re
import decimal
from django.db import transaction
from django.utils import timezone
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

PHONE_REGEX = re.compile(r"^(\+\d{7,15}|\d{3}-\d{3}-\d{4})$")

# GraphQL Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        fields = ("id","name","email","phone","created_at","updated_at")
        filterset_class = CustomerFilter

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        fields = ("id","name","price","stock","created_at","updated_at")
        filterset_class = ProductFilter

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        fields = ("id","customer","products","total_amount","order_date","created_at","updated_at")
        filterset_class = OrderFilter

# Inputs
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(default_value=0)

class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()

# Mutations
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)
    customer = graphene.Field(CustomerType)
    message = graphene.String()
    ok = graphene.Boolean()

    @staticmethod
    def mutate(root, info, input: CustomerInput):
        email = input.email.strip().lower()
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")
        phone = input.phone.strip() if input.phone else None
        if phone and not PHONE_REGEX.match(phone):
            raise Exception("Invalid phone format. Use +1234567890 or 123-456-7890")
        customer = Customer.objects.create(name=input.name.strip(), email=email, phone=phone)
        return CreateCustomer(customer=customer, message="Customer created", ok=True)

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        created = []
        errors = []
        with transaction.atomic():
            for idx, c in enumerate(input, start=1):
                try:
                    email = c.email.strip().lower()
                    if Customer.objects.filter(email=email).exists():
                        raise Exception(f"Row {idx}: Email already exists")
                    phone = c.phone.strip() if c.phone else None
                    if phone and not PHONE_REGEX.match(phone):
                        raise Exception(f"Row {idx}: Invalid phone format")
                    obj = Customer(name=c.name.strip(), email=email, phone=phone)
                    obj.save()
                    created.append(obj)
                except Exception as e:
                    errors.append(str(e))
        return BulkCreateCustomers(customers=created, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)
    product = graphene.Field(ProductType)

    @staticmethod
    def mutate(root, info, input: ProductInput):
        if decimal.Decimal(input.price) <= 0:
            raise Exception("Price must be positive")
        if input.stock is not None and input.stock < 0:
            raise Exception("Stock cannot be negative")
        prod = Product.objects.create(name=input.name.strip(), price=input.price, stock=input.stock or 0)
        return CreateProduct(product=prod)

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)
    order = graphene.Field(OrderType)

    @staticmethod
    def mutate(root, info, input: OrderInput):
        # Validate customer
        try:
            cust_pk = relay.Node.from_global_id(input.customer_id)[1] if input.customer_id and ":" in input.customer_id else input.customer_id
            customer = Customer.objects.get(pk=cust_pk)
        except Exception:
            raise Exception("Invalid customer ID")

        # Validate products
        if not input.product_ids:
            raise Exception("At least one product must be selected")
        product_pks = []
        for pid in input.product_ids:
            try:
                pk = relay.Node.from_global_id(pid)[1] if pid and ":" in pid else pid
                product_pks.append(int(pk))
            except Exception:
                raise Exception("Invalid product ID")

        products = list(Product.objects.filter(id__in=product_pks))
        if len(products) != len(product_pks):
            raise Exception("One or more product IDs are invalid")

        order = Order.objects.create(customer=customer, order_date=input.order_date or timezone.now())
        order.products.set(products)
        order.recalc_total()
        return CreateOrder(order=order)

# Query with filtering and ordering
class Query(graphene.ObjectType):
    node = relay.Node.Field()

    # Filterable connections
    all_customers = DjangoFilterConnectionField(CustomerType, order_by=graphene.List(graphene.String))
    all_products = DjangoFilterConnectionField(ProductType, order_by=graphene.List(graphene.String))
    all_orders = DjangoFilterConnectionField(OrderType, order_by=graphene.List(graphene.String))

    def resolve_all_customers(root, info, **kwargs):
        qs = Customer.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products(root, info, **kwargs):
        qs = Product.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders(root, info, **kwargs):
        qs = Order.objects.all().distinct()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
