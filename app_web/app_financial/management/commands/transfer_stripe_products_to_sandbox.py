"""
This is a command meant only for local and dev environments.
It takes all the products and prices from LIVE_SECRET_KEY Stripe and recreates
them in the TEST_SECRET_KEY Stripe account.

Attention: Clean up command can't remove all data, some may need to be removed
manually. Delete Manually Products, Prices, and Customers from the Stripe
Dashboard, then run this command.
"""
import os

import stripe
import time
from django.core.management.base import BaseCommand

LIVE_SECRET_KEY = os.getenv('LIVE_SECRET_KEY')
TEST_SECRET_KEY = os.getenv('TEST_SECRET_KEY')

if not LIVE_SECRET_KEY or not TEST_SECRET_KEY:
    raise ValueError("Stripe API keys not set in environment variables.")


class Command(BaseCommand):
    def handle(self, *args, **options):
        # self.cleanup_test_environment()
        self.populate_prices()

    @staticmethod
    def cleanup_test_environment():
        # Set the API key to the test environment
        stripe.api_key = TEST_SECRET_KEY

        print("Cleaning up test environment...")

        # Delete existing subscriptions
        subscriptions = stripe.Subscription.list()
        for subscription in subscriptions.auto_paging_iter():
            try:
                stripe.Subscription.delete(subscription['id'])
                print(
                    f"Deleted subscription {subscription['id']} in test environment.")
            except Exception as e:
                print(f"Error deleting subscription {subscription['id']}: {e}")

        # Delete existing customers
        customers = stripe.Customer.list()
        for customer in customers.auto_paging_iter():
            try:
                stripe.Customer.delete(customer['id'])
                print(f"Deleted customer {customer['id']} in test environment.")
            except Exception as e:
                print(f"Error deleting customer {customer['id']}: {e}")

        # Deactivate existing prices (prices cannot be deleted via the API)
        prices = stripe.Price.list()
        for price in prices.auto_paging_iter():
            try:
                stripe.Price.modify(price['id'], active=False)
                print(f"Deactivated price {price['id']} in test environment.")
            except Exception as e:
                print(f"Error deactivating price {price['id']}: {e}")

        # Attempt to delete existing products
        products = stripe.Product.list()
        for product in products.auto_paging_iter():
            try:
                # Attempt to delete the product
                stripe.Product.delete(product['id'])
                print(f"Deleted product {product['id']} in test environment.")
            except stripe.error.InvalidRequestError as e:
                # If product cannot be deleted due to associated prices, deactivate it
                print(f"Cannot delete product {product['id']}: {e}")
                try:
                    stripe.Product.modify(product['id'], active=False)
                    print(
                        f"Deactivated product {product['id']} in test environment.")
                except Exception as e:
                    print(f"Error deactivating product {product['id']}: {e}")
            except Exception as e:
                print(f"Error deleting product {product['id']}: {e}")

        print("Test environment cleanup completed.")

    def populate_prices(self):
        # Set the API key to the live environment
        stripe.api_key = LIVE_SECRET_KEY

        # Fetch all products from the live environment
        live_products = stripe.Product.list(limit=100)
        print("Fetched products from live environment.")

        # Fetch all prices from the live environment
        live_prices = stripe.Price.list(limit=100)
        print("Fetched prices from live environment.")

        # Store product and price data
        products_data = [product for product in live_products.auto_paging_iter()]
        prices_data = []

        # Fetch prices with expanded tiers if needed
        for price in live_prices.auto_paging_iter():
            if price.get('billing_scheme') == 'tiered':
                try:
                    price_with_tiers = stripe.Price.retrieve(
                        price['id'],
                        expand=['tiers']
                    )
                    price = price_with_tiers
                except Exception as e:
                    print(f"Error fetching price {price['id']} with tiers: {e}")
            prices_data.append(price)

        # Switch to the test environment
        stripe.api_key = TEST_SECRET_KEY

        # Clean up the test environment
        self.cleanup_test_environment()

        # Mapping from live product IDs to test product IDs
        product_id_mapping = {}

        # Recreate products in the test environment
        for product in products_data:
            product_params = {
                'name': product['name'],
                'description': product.get('description', ''),
                'metadata': product.get('metadata', {}),
                'shippable': product.get('shippable', False),
                'url': product.get('url'),
                'images': product.get('images', []),
                'active': product.get('active', True),
            }

            new_product = stripe.Product.create(**product_params)
            print(f"Created product {new_product['id']} in test environment.")

            product_id_mapping[product['id']] = new_product['id']
            time.sleep(0.5)  # Avoid hitting rate limits

        # Recreate prices in the test environment
        for price in prices_data:
            new_product_id = product_id_mapping.get(price['product'])
            if not new_product_id:
                print(f"Product ID {price['product']} not found in mapping.")
                continue

            # Prepare base price parameters
            price_params = {
                'currency': price['currency'],
                'product': new_product_id,
                'nickname': price.get('nickname'),
                'metadata': price.get('metadata', {}),
                'billing_scheme': price.get('billing_scheme', 'per_unit'),
            }

            # Include recurring parameters if applicable
            if price['type'] == 'recurring':
                price_params['recurring'] = {
                    'interval': price['recurring']['interval'],
                    'interval_count': price['recurring'].get('interval_count', 1),
                    'usage_type': price['recurring'].get('usage_type'),
                    'aggregate_usage': price['recurring'].get('aggregate_usage'),
                }

            # Handle tiered billing scheme
            if price.get('billing_scheme') == 'tiered':
                price_params['tiers_mode'] = price.get('tiers_mode')

                if price.get('tiers'):
                    # Process tiers and ensure 'up_to' is correctly set
                    tiers = []
                    num_tiers = len(price['tiers'])

                    for idx, tier in enumerate(price['tiers']):
                        tier_params = {
                            'unit_amount': tier.get('unit_amount'),
                            'flat_amount_in_cents': tier.get(
                                'flat_amount_in_cents'
                            ),
                        }

                        if idx == num_tiers - 1:
                            # Last tier should have 'up_to' set to 'inf'
                            tier_params['up_to'] = "inf"
                        else:
                            if tier.get('up_to') is not None:
                                tier_params['up_to'] = tier['up_to']
                            else:
                                print(
                                    f"Missing 'up_to' in tier {idx} for price "
                                    f"{price['id']}"
                                )
                                continue

                        tiers.append(tier_params)

                    if not tiers:
                        print(
                            f"No valid tiers found for price {price['id']}. "
                            f"Skipping."
                        )
                        continue

                    price_params['tiers'] = tiers
                else:
                    print(
                        f"Price {price['id']} has billing_scheme 'tiered' but "
                        f"no tiers found."
                    )
                    continue

                # Do not include unit_amount for tiered prices
                price_params.pop('unit_amount', None)
            else:
                # For per_unit billing_scheme
                if price['unit_amount'] is not None:
                    price_params['unit_amount'] = price['unit_amount']
                else:
                    print(f"Price {price['id']} has no unit_amount. Skipping.")
                    continue

            # Include transform_quantity if present
            if price.get('transform_quantity'):
                price_params['transform_quantity'] = price.get(
                    'transform_quantity')

            # Create the price in the test environment
            try:
                new_price = stripe.Price.create(**price_params)
                print(
                    f"Created price {new_price['id']} "
                    f"for product {new_product_id} in test environment."
                )
            except Exception as e:
                print(f"Error creating price for product {new_product_id}: {e}")
            time.sleep(0.5)  # Avoid hitting rate limits

        print("Data transfer from live to test environment completed.")
