import os
from datetime import datetime, timedelta
from datetime import date
import math

import stripe

from django.db import models, IntegrityError
from django.db.models import Q
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import make_aware


stripe.api_key = os.environ.get("STRIPE_SECRET")


def timestamp_to_datetime(timestamp):
    if timestamp is None:
        return None
    if isinstance(timestamp, int):
        timestamp = date.fromtimestamp(timestamp)
    return make_aware(datetime.combine(timestamp, datetime.now().time()))


class RequiredLocalInstances(Exception):
    pass


class CustomerManager(models.Manager):
    def sync_subscriptions(self):
        for customer in self.all():
            print("user", customer.user.username)
            customer.sync_subscriptions()


# Create your models here.
class Customer(models.Model):
    USD = "usd"
    CURRENCY_CHOICES = ((USD, "usd"),)

    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    account_balance = models.DecimalField(
        decimal_places=2, max_digits=9, null=True, blank=True
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    delinquent = models.BooleanField(default=False)
    default_source = models.TextField(blank=True, null=True)
    metadata = JSONField()

    objects = CustomerManager()

    def cancel_subscriptions(self):
        subscriptions = self.subscriptions.all()
        for sub in subscriptions:
            stripe_sub = Subscription.get_stripe_object(sub.stripe_id)
            stripe_sub.cancel_at_period_end = True
            updated_sub = stripe_sub.save()
            sub.update_from_stripe_obj(updated_sub)

    def update_source(self, stripe_token):
        stripe_customer = stripe.Customer.retrieve(self.stripe_id)
        stripe_customer.source = stripe_token
        stripe_customer.save()
        self.default_source = stripe_token
        self.save()

    def sync_subscriptions(self):
        public_plans = Plan.get_public_plans(usage_type="metered")
        do_update = True
        try:
            sub = self.subscriptions.get(subscription_type="primary")
            curr_plans = [plan.id for plan in sub.plans.all()]
            not_subscribed = public_plans.filter(
                ~Q(id__in=curr_plans), usage_type="metered"
            )
            # Don't call stripe api with empty list of plans!
            if not_subscribed:
                print(
                    "adding plans: ",
                    self.user.username,
                    [ns.nickname for ns in not_subscribed],
                )
                stripe_sub = stripe.Subscription.modify(
                    sub.stripe_id,
                    items=[{"plan": plan.stripe_id} for plan in not_subscribed],
                )
                sub.plans.add(*not_subscribed)
                sub.save()
            else:
                # no need to update.
                do_update = False
        except Subscription.DoesNotExist:
            stripe_sub = Subscription.create_stripe_object(self, public_plans)
            sub = Subscription.construct(
                stripe_sub, self, public_plans, subscription_type="primary"
            )
        if do_update:
            for raw_si in stripe_sub["items"]["data"]:
                stripe_si = SubscriptionItem.get_stripe_object(raw_si["id"])
                plan = public_plans.get(stripe_id=raw_si["plan"]["id"])
                si, created = SubscriptionItem.get_or_construct(stripe_si.id, plan, sub)

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Customer.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_customer, user=None):
        customer = Customer.objects.create(
            stripe_id=stripe_customer.id,
            livemode=stripe_customer.livemode,
            user=user,
            account_balance=stripe_customer.account_balance,
            currency=stripe_customer.currency or "usd",
            delinquent=stripe_customer.delinquent,
            default_source=stripe_customer.default_source,
            metadata=stripe_customer.to_dict(),
        )
        return customer

    @staticmethod
    def get_or_construct(stripe_id, user=None):
        """
        Try to get existing customer. If customer does not exist, retrieve
        customer from Stripe and construct local customer

        returns:
        customer: customer instance
        created: indicates whether a new customer was created
        """
        try:
            customer, created = Customer.objects.get(stripe_id=stripe_id), False
        except Customer.DoesNotExist as dne:
            stripe_obj = Customer.get_stripe_object(stripe_id)
            customer, created = Customer.construct(stripe_obj, user), True
        except IntegrityError:
            customer, created = Customer.objects.get(stripe_id=stripe_id), False
        return customer, created


class Product(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    project = models.OneToOneField("users.Project", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    metadata = JSONField()

    @staticmethod
    def create_stripe_object(name):
        product = stripe.Product.create(name=name, type="service")
        return product

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Product.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_product, project):
        product = Product.objects.create(
            stripe_id=stripe_product.id,
            project=project,
            name=stripe_product.name,
            metadata=stripe_product.to_dict(),
        )
        return product

    @staticmethod
    def get_or_construct(stripe_id, project=None):
        try:
            product, created = Product.objects.get(stripe_id), False
        except Product.DoesNotExist:
            if product is None:
                raise RequiredLocalInstances(
                    "Local instance of Project was not provided."
                )
            stripe_obj = Product.get_stripe_object(stripe_id)
            product, created = Product.construct(stripe_obj, project), True
        except IntegrityError:
            product, created = Product.objects.get(stripe_id), False
        return (product, created)


class Plan(models.Model):
    LICENSED = "licensed"
    METERED = "metered"
    USAGE_TYPE_CHOICES = ((LICENSED, "licensed"), (METERED, "metered"))

    SUM = "sum"
    LAST_DURING_PERIOD = "last_during_period"
    MAX = "max"
    LAST_EVER = "last_ever"
    AGG_USAGE_CHOICES = (
        (SUM, "sum"),
        (LAST_DURING_PERIOD, "last_during_period"),
        (MAX, "max"),
        (LAST_EVER, "LAST_EVER"),
    )

    USD = "usd"
    CURRENCY_CHOICES = ((USD, "usd"),)

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    INTERVAL_CHOICES = ((DAY, "day"), (WEEK, "week"), (MONTH, "month"), (YEAR, "year"))
    stripe_id = models.CharField(max_length=255, unique=True)
    active = models.BooleanField(default=False)
    aggregate_usage = models.CharField(
        max_length=18, choices=AGG_USAGE_CHOICES, default=SUM, null=True
    )
    amount = models.IntegerField()
    created = models.DateTimeField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    interval = models.CharField(max_length=5, choices=INTERVAL_CHOICES, default=MONTH)
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    nickname = models.CharField(max_length=255)
    product = models.ForeignKey(
        Product, null=True, on_delete=models.CASCADE, related_name="plans"
    )
    trial_period_days = models.IntegerField(default=0, null=True)
    usage_type = models.CharField(max_length=8, choices=USAGE_TYPE_CHOICES)

    @staticmethod
    def create_stripe_object(
        amount, product, usage_type, interval="month", currency="usd"
    ):
        nickname = f"{product.name} {usage_type.title()} {currency}"
        plan = stripe.Plan.create(
            amount=amount,
            nickname=nickname,
            product=product.stripe_id,
            usage_type=usage_type,
            interval=interval,
            currency=currency,
        )
        return plan

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Plan.get(stripe_id)

    @staticmethod
    def construct(stripe_plan, product):
        plan = Plan.objects.create(
            stripe_id=stripe_plan.id,
            active=stripe_plan.active,
            aggregate_usage=stripe_plan.aggregate_usage,
            amount=stripe_plan.amount,
            created=timestamp_to_datetime(stripe_plan.created),
            currency=stripe_plan.currency,
            interval=stripe_plan.interval,
            livemode=stripe_plan.livemode,
            metadata=stripe_plan.to_dict(),
            nickname=stripe_plan.nickname,
            product=product,
            trial_period_days=stripe_plan.trial_period_days,
            usage_type=stripe_plan.usage_type,
        )
        return plan

    @staticmethod
    def get_or_construct(stripe_id, product=None):
        try:
            plan, created = Plan.objects.get(stripe_id=stripe_id), False
        except Plan.DoesNotExist:
            if product is None:
                raise RequiredLocalInstances(
                    "Local instance of Product was not provided."
                )
            stripe_plan = Plan.get_stripe_object(stripe_id)
            plan, created = Plan.construct(stripe_plan, product), True
        except IntegrityError:
            plan, created = Plan.objects.get(stripe_id), False
        return (plan, created)

    @staticmethod
    def get_public_plans(**kwargs):
        return Plan.objects.filter(product__project__is_public=True, **kwargs)


class Subscription(models.Model):
    # raises error on deletion
    subscription_type = models.CharField(
        default="primary", choices=[("primary", "Primary")], max_length=50
    )
    stripe_id = models.CharField(max_length=255, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plans = models.ManyToManyField(Plan, related_name="subscriptions")
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    cancel_at_period_end = models.BooleanField(default=False, null=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def update_from_stripe_obj(self, stripe_obj):
        self.current_period_start = timestamp_to_datetime(
            stripe_obj.current_period_start
        )
        self.current_period_end = timestamp_to_datetime(stripe_obj.current_period_end)
        self.cancel_at_period_end = stripe_obj.cancel_at_period_end
        self.canceled_at = timestamp_to_datetime(stripe_obj.canceled_at)
        self.ended_at = timestamp_to_datetime(stripe_obj.ended_at)
        self.save()

    @staticmethod
    def create_stripe_object(customer, plans):
        subscription = stripe.Subscription.create(
            customer=customer.stripe_id,
            items=[{"plan": plan.stripe_id} for plan in plans],
        )
        return subscription

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Subscription.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription, customer, plans, subscription_type="primary"):
        current_period_start = timestamp_to_datetime(
            stripe_subscription.current_period_start
        )
        current_period_end = timestamp_to_datetime(
            stripe_subscription.current_period_end
        )
        sub = Subscription.objects.create(
            stripe_id=stripe_subscription.id,
            customer=customer,
            livemode=stripe_subscription.livemode,
            metadata=stripe_subscription.to_dict(),
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            subscription_type="primary",
        )
        sub.plans.add(*plans)
        sub.save()
        return sub

    @staticmethod
    def get_or_construct(stripe_id, customer=None, plans=None):
        try:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        except Subscription.DoesNotExist:
            if not customer or not plans:
                raise RequiredLocalInstances(
                    "Local instances of Customer and Plan were not provided."
                )
            stripe_obj = Subscription.get_stripe_object(stripe_id)
            subscription, created = (
                Subscription.construct(stripe_obj, customer, plans),
                True,
            )
        except IntegrityError:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        return (subscription, created)

    def extend_subscription(self, days=30):
        """
        Extend subscription a month from its end date or now
        if "now" is after the subscription ended.
        """
        base = max(make_aware(datetime.now()), self.current_period_end)

        self.current_period_end = base + timedelta(days=days)

    def cancel_subscription(self):
        self.canceled_at = make_aware(datetime.now())
        # allowed to use site until current period is over
        self.ended_at = self.current_period_end


class SubscriptionItem(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    created = models.DateTimeField()
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="subscription_items", null=True
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="subscription_items"
    )

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.SubscriptionItem.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription_item, plan, subscription):
        created = timestamp_to_datetime(stripe_subscription_item.created)
        subscription_item = SubscriptionItem.objects.create(
            stripe_id=stripe_subscription_item.id,
            livemode=subscription.livemode,  # stripe obj doesn't have livemode
            created=created,
            plan=plan,
            subscription=subscription,
        )
        return subscription_item

    @staticmethod
    def get_or_construct(stripe_id, plan=None, subscription=None):
        try:
            si, created = SubscriptionItem.objects.get(stripe_id=stripe_id), False
        except SubscriptionItem.DoesNotExist:
            if plan is None or subscription is None:
                raise RequiredLocalInstances(
                    "Local instances of Plan and Subscription were not provided."
                )
            stripe_si = SubscriptionItem.get_stripe_object(stripe_id)
            si, created = (
                SubscriptionItem.construct(stripe_si, plan, subscription),
                True,
            )
        except IntegrityError:
            si, created = SubscriptionItem.objects.get(stripe_id), False
        return (si, created)


class UsageRecord(models.Model):
    INC = "increment"
    SET = "set"
    ACTION_CHOICES = ((INC, "increment"), (SET, "set"))
    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    action = models.CharField(max_length=9, choices=ACTION_CHOICES, default=INC)
    quantity = models.IntegerField(default=0)
    subscription_item = models.ForeignKey(
        SubscriptionItem, on_delete=models.CASCADE, related_name="usage_records"
    )
    timestamp = models.DateTimeField()

    @staticmethod
    def create_stripe_object(
        quantity, timestamp, subscription_item, action="increment"
    ):
        stripe_usage_record = stripe.UsageRecord.create(
            quantity=quantity,
            # None implies now
            timestamp=timestamp or math.floor(datetime.now().timestamp()),
            subscription_item=subscription_item.stripe_id,
            action=action,
        )
        return stripe_usage_record

    @staticmethod
    def get_stripe_object(stripe_id):
        """
        `stripe.UsageRecord` does not have a `get` method
        """
        raise NotImplementedError()

    @staticmethod
    def construct(stripe_usage_record, subscription_item):
        print("construct", stripe_usage_record)
        usage_record = UsageRecord.objects.create(
            stripe_id=stripe_usage_record.id,
            livemode=stripe_usage_record.livemode,
            quantity=stripe_usage_record.quantity,
            subscription_item=subscription_item,
            timestamp=timestamp_to_datetime(stripe_usage_record.timestamp),
        )
        return usage_record

    @staticmethod
    def get_or_construct(stripe_id, subscription_item=None):
        try:
            (usage_record, created) = (
                UsageRecord.objects.get(stripe_id=stripe_id),
                False,
            )
        except IntegrityError:
            usage_record, created = UsageRecord.objects.get(stripe_id), False
        return (usage_record, created)


class Event(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField()
    data = JSONField()
    livemode = models.BooleanField(default=False)
    # pending_webhooks = models.IntegerField()
    request = models.CharField(max_length=255)
    kind = models.CharField(max_length=64)  # maps to stripe:type
    customer = models.ForeignKey(
        Customer, null=True, on_delete=models.CASCADE, related_name="customer"
    )
    metadata = JSONField()

    @staticmethod
    def construct(stripe_event, customer=None, invoice=None):
        event = Event.objects.create(
            stripe_id=stripe_event.id,
            created=timestamp_to_datetime(stripe_event.created),
            customer=customer,
            data=stripe_event["data"],
            livemode=stripe_event.livemode,
            kind=stripe_event.type,
            metadata=stripe_event.to_dict(),
        )
        return event


def create_billing_objects(project):
    if not hasattr(project, "product") or project.product is None:
        owner = project.owner.user.username
        title = project.title
        name = f"{owner}/{title}"
        print("creating billing objects for ", name)
        stripe_product = Product.create_stripe_object(name)
        product = Product.construct(stripe_product, project)
        stripe_plan_lic = Plan.create_stripe_object(
            amount=0,
            product=product,
            usage_type="licensed",
            interval="month",
            currency="usd",
        )
        Plan.construct(stripe_plan_lic, product)
        stripe_plan_met = Plan.create_stripe_object(
            amount=1,
            product=product,
            usage_type="metered",
            interval="month",
            currency="usd",
        )
        Plan.construct(stripe_plan_met, product)
