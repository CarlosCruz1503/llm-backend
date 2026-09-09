from restaurant.models import Restaurant


def get_default_restaurant():
    """This is a single-restaurant deployment (your friend's restaurant, not
    a multi-tenant platform), so tools that need "the" restaurant just grab
    the first row rather than requiring a restaurant_id from the caller/LLM.
    Returns None if `seed_restaurant` hasn't been run yet.
    """
    return Restaurant.objects.order_by("pk").first()
