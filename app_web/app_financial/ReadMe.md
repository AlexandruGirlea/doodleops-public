# 1. How credits work

- user buys credits;
- we allocate credits to user in `CustomerCreditsBought` based the
`convert_cents_into_credit` method;
- we create a new Redis key `REDIS_KEY_USER_CREDIT_BOUGHT` with the schema
`user_credit_bought:{username}:{id}` we don't set any expiration;
- each time the user calls an API and consumes credits we decrement them
from the Redis key starting with the lowest `id` of that `username`;

### 1.1 How we expire credits:
- we run a cron job at the beginning of each day that loops through all the 
users in `user_credit_bought` key if they match the `id` of an expired
purchase, we remove it from the Redis DB.

### 1.2 In order to keep SQL DB and Redis DB in sync we do the following:
- we run a cronjob every 2h that stores the number of total credits for each user
with a `created` timestamp in a new table `CustomerCreditsTotal`;

In case of data loss in redis we can recover the user credits based on the stored
`CustomerCreditsTotal` table.

OBS: if the use has no credits bought or the amount of credit did not change
since last time we stored the total credits, we don't store anything in the
`CustomerCreditsTotal` table.


# 2. How NON Metered Subscriptions work

- user buys a subscription;
- we create 1 Redis Key `REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING` with 
  the schema `"subscriptions_monthly_credit_remaining:{username}"`. This key will
  indicate how many API units the user has left for the current month;

# 3. How a Metered Subscription works (Enterprise)

### 3.1 General info:
- we should have at most 1 subscription of type metered (the code will fail if we 
  have more than 1);
- we DO NOT set Redis Key `REDIS_KEY_SUBSCRIPTIONS_MONTHLY_CREDIT_REMAINING`
- we DO SET a Redis Key `REDIS_KEY_METERED_SUBSCRIPTION_USERS` so that we know
  if a user has a metered subscription or not;

### 3.2 How billing works:

- When a user subscribes to a metered subscription, stripe sends a webhook
  `invoice.created` to our backend with active set to `true`;

- Because of time differences (User / Stripe / Django server time zones) we can't 
  use the exact timestamp for determining the START and END of a billing 
  period. Instead, we use the following logic:
    - the user might be in a different timezone than the Stripe server, and the 
      Stripe server might be in a different timezone than our Django Server.
      We don't care, because we only use our Django Server Time (UTC) to calculate
      the beginning and end of days based on the timestamp sent by Stripe;
    - we convert the START timestamp sent by Stripe to UTC Date ("%d-%m-%Y");
    - we convert the END timestamp sent by Stripe to UTC Date ("%d-%m-%Y");
    - we create APICounter objects for each day between the START and END date
      and set the date to the UTC Date `("%d-%m-%Y")`;
    - we bill APICounter objects between `date__gt=START` and 
      `date__lt=END` + credits used in the day the subscription started 
      (current_period_start) and the day the subscription ended
      (current_period_end). We get these values from Redis;

- Between the time the user subscribes and the time the subscription monthly
  update webhook is sent, we use the 
  `cronjob_store_api_counter_obj_for_the_previous_day` function to
  create APICounter objects for all subscribed metered users for the previous 
  day. Each time we create an APICounter object we set the timestamp to the date
  it was recorded in Redis. Because this cronjob is run every 3 hours (so that
  we don't lose too much data / revenue if Redis goes down), we not only create
  new API Counter objects, but we also update the existing ones.

- Every 3h we run `cronjob_send_subscription_item_metered_usage_to_stripe`.

- When we receive a webhook `subscription.updated` renew billing cycle, we
  send the metered usage to stripe for the period between the START and End
  of the billing cycle timestamps.
  We use the timestamp of the END of the billing cycle `-1` second.
  Because the `cronjob_store_api_counter_obj_for_the_previous_day` might
  have not run yet, we run it again providing a `username`, so that we can have
  the updated APICounter objects for the previous day, that we use to SUM the 
  total number of API calls for the billing cycle.

### 3.3 How `get_instant_cost_for_metered_subscription` works:

- This will only work based on internal usage calculations and not based on
  Stripe usage / estimation invoice;

### 3.4 How to manually get estimated cost for a customer

```bash
python manage.py shell
```

```python
import stripe; stripe.Invoice.upcoming(customer="cus_PEcwtYJBCLDhxY").total
```
  
# 4. How to create Pricing Plans (total 8)

Go to the [Product Catalog page](https://dashboard.stripe.com/test/products) and
create a product based on the below info. It will automatically create a price.

### 4.1 Enterprise (metered) Pricing Plan (1 price):
Make sure that the Enterprise subs has:
- Pricing Model: `Volume pricing`
- Usage type: `Metered usage`
- Aggregation mode: `Last value during period`
- Charge for metered usage by: `Most recent usage value during the period`
- Price Metadata set like this:
```bash
1: {"start":1, "end": 100000, "price_in_cents":1, "flat_amount_in_cents": 1500}
2: {"start":100001, "end": 500000, "price_in_cents":0.9, "flat_amount_in_cents": 0}
3: {"start":500001, "price_in_cents":0.8, "flat_amount_in_cents": 0}
```
OBS: the above start and end values represent the number of credits used per billing cycle.
OBS2: the base price should be the max price of the previous tier. See above.
OBS3: the `api_daily_call_limit` metadata is for Product, NOT for Price. Set this
for all subscriptions.

### 4.2 Non Enterprise Pricing Plan (4 prices):
Make sure that the price has:
- Usage type: `Recurring usage`

Create 1 Product (Base / Pro) and then, for each create 2 prices:
- Interval: `Monthly` and `Yearly`

For example:
- 5 credits per month and 50 credits per year (Base)
- 10 credits per month and 100 credits per year (Pro)

### 4.3 Buy credit Pricing Plan (3 prices):
Make sure that the price has:
- Interval `One-time`

For example:
- Name: `5$` - Description: `Buy 50 credits`
- Name: `10$` - Description: `Buy 100 credits`
- Name: `20$` - Description: `Buy 200 credits`

# 5. Billing Info

### 5.1 How to enable VAT number for customers

Go to Stripe Dashboard -> Settings -> Customer portal -> Customer information
and enable VAT number.


# 6. Enable One Customer One Subscription Limit in Stripe

Dashboard -> Checkout and Payment Links -> Limit subscriptions to one per customer

# 7. Use the following command to copy products and prices from one env to another
OBS: This does not fully work with Enterprise, we still need to manually set that.
Read the above.
```bash
make bash cont=web

LIVE_SECRET_KEY="secret" TEST_SECRET_KEY="secret" python manage.py transfer_stripe_products_to_sandbox
```
