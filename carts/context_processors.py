from .models import Cart, CartItem
from .views import _cart_id


def counter(request):
    cart_count = 0
    if 'admin' in request.path:
        return []
    else:
        try:
            cart = Cart.objects.filter(cart_id=_cart_id(request)) # get the cart using the cart_id present in the session
            cart_items = CartItem.objects.all().filter(cart=cart[:1]) # get first cart item using the cart_id
            for cart_item in cart_items:
                cart_count += cart_item.quantity
        except Cart.DoesNotExist:
            cart_count = 0
    return dict(cart_count=cart_count)
