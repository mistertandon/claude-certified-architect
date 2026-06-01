"""Sample Python file to be analyzed by the code reviewer."""


def calculate_shipping(weight, destination, is_express, discount_code=None):
    base_rate = 5.99
    if weight > 50:
        base_rate = 15.99
    elif weight > 20:
        base_rate = 10.99
    elif weight > 10:
        base_rate = 7.99

    if destination == "international":
        base_rate *= 2.5
    elif destination == "remote":
        base_rate *= 1.75

    if is_express:
        base_rate *= 1.5

    if discount_code == "FREESHIP":
        base_rate = 0
    elif discount_code == "HALF":
        base_rate *= 0.5

    tax = base_rate * 0.08
    total = base_rate + tax
    return round(total, 2)


def process_order(
    order_id, items, customer, payment, shipping_address,
    billing_address, notes, gift_wrap, insurance, tracking,
    notification_preference, delivery_instructions, signature_required,
    age_verification, hazmat_flag, temperature_control,
    customs_declaration, return_label, priority_level, batch_id,
):
    validated_items = []
    for item in items:
        if item.get("quantity", 0) > 0:
            if item.get("price", 0) > 0:
                if item.get("sku"):
                    validated_items.append(item)
                else:
                    raise ValueError(f"Missing SKU for item: {item}")
            else:
                raise ValueError(f"Invalid price for item: {item}")
        else:
            raise ValueError(f"Invalid quantity for item: {item}")

    subtotal = sum(i["price"] * i["quantity"] for i in validated_items)

    if payment["method"] == "credit_card":
        if len(payment.get("card_number", "")) != 16:
            raise ValueError("Invalid card number")
        if not payment.get("expiry"):
            raise ValueError("Missing expiry date")
        if not payment.get("cvv"):
            raise ValueError("Missing CVV")
    elif payment["method"] == "paypal":
        if not payment.get("email"):
            raise ValueError("Missing PayPal email")
    elif payment["method"] == "bank_transfer":
        if not payment.get("account_number"):
            raise ValueError("Missing account number")
        if not payment.get("routing_number"):
            raise ValueError("Missing routing number")

    shipping_cost = calculate_shipping(
        sum(i.get("weight", 0) * i["quantity"] for i in validated_items),
        shipping_address.get("type", "domestic"),
        priority_level == "express",
    )

    if gift_wrap:
        subtotal += len(validated_items) * 3.99

    if insurance:
        subtotal += subtotal * 0.02

    tax_rate = 0.08
    if shipping_address.get("state") in ("OR", "MT", "NH", "DE"):
        tax_rate = 0.0
    tax = subtotal * tax_rate

    total = subtotal + tax + shipping_cost

    order = {
        "order_id": order_id,
        "items": validated_items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "shipping": shipping_cost,
        "total": round(total, 2),
        "status": "confirmed",
    }

    return order


def add(a, b):
    return a + b
