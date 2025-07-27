# Stripe CLI

OBS: whenever you see below stuff like `-d [something][something_else]` this means
that is a nested flag that needs  to be set.

### More info can be found here: 
[Get started with the Stripe CLI](https://docs.stripe.com/stripe-cli)
```bash
brew install stripe/stripe-cli/stripe
stripe login
# or use api key
stripe login --api-key sk_test_51Nmwe123
# list the stripe config
stripe config --list
```
 
### How to create a dummy customer in Stripe from the CLI

The payment methods can be found 
[HERE](https://stripe.com/docs/testing?testing-method=payment-methods).
```bash
stripe customer create
# or in more detaile
stripe customer create --email test@doodleops.com --payment-method pm_card_visa \
-d invoice_settings[default_payment_method]=pm_card_visa
# get user data for any customer
stripe customers retrieve {customer_stripe_id}
```

### How to create a subscription for a customer. 
This will subscribe an existing user to an existing plan, it will create a 
subscription object and we can also get the payed invoice ID.
```bash
# list all the plans a user can be subscribed to
stripe plans list
# subscribe a user to a plan
stripe subscriptions create --customer {customer_stripe_id} \
-d items[][plan]={scubscription_plan_name}
```
a bunny riding a 4 wheel bike down a mountain .
### For easy processing install JQ

```bash
brew install jq
# try it out
stripe customers list | jq '.data[].id'
stripe customers list | jq '.data[] | {id, name, email}'
```


### How to use Stripe Listen for development
- This listening for any Stripe events
```bash
stripe listen
```
- Trigger a stripe Event
```bash
stripe customers create
# or predefined triggers for testing
stripe trigger checkout.session.completed
```
- Listen for specific events
```bash
stripe listen --events checkout.session.completed,payment_intent.succeeded
# we can add `-j`to get an JSON output
stripe listen --events checkout.session.completed,payment_intent.succeeded -j
```
- Forward events to local web-hook server

```bash
stripe listen --forward-to localhost:8000/stripe-webhooks
```
OBS: in case an event did not trigger or we want to run it again we can do this
```bash
# this will output a json response
stripe events retrieve {stripe_event_id}
# and if we want to retry processing the event in case our Web-hook had an error
stripe events resend {stripe_event_id}
```