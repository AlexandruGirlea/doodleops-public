# Stripe

### 1.2 If stripe webhook local test fails
```bash
# if this fails
stripe listen --forward-to http://127.0.0.1:8000/financial/stripe-webhook/

# run this
stripe login

# now run the above command again
```


# Celery

### 2.1 How to list all Celery tasks
```bash
make bash cont=celery_beat

celery -A core inspect registered
->  celery@fbe15b3a7581: OK
    * app_api.tasks.cronjob_store_api_counter_obj_for_the_previous_day
    * app_api.tasks.has_api_counter_discrepancies
    * app_api.tasks.process_user_batch
    * app_financial.tasks.cronjob_send_subscription_item_metered_usage_to_stripe
    * app_financial.tasks.remove_credits_older_than_one_year
```

### 2.2 Celery Beat