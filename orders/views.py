import datetime
import json

from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from liqpay.liqpay import LiqPay

from carts.models import CartItem
from store.models import Product
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from shop.settings import PUBLIC_KEY, PRIVATE_KEY


from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import HttpResponse

# class PayView(TemplateView):
#
#     template_name = 'orders/payments.html'
#
#     def get(self, request, *args, **kwargs):
#         liqpay = LiqPay(PUBLIC_KEY, PRIVATE_KEY)
#         params = {
#             'action': 'pay',
#             'amount': '100',
#             'currency': 'USD',
#             'description': 'Payment for clothes',
#             'order_id': 'order_id_1',
#             'version': '3',
#             'sandbox': 0, # sandbox mode, set to 1 to enable it
#             'server_url': 'https://test.com/billing/pay-callback/', # url to callback view
#         }
#         signature = liqpay.cnb_signature(params)
#         data = liqpay.cnb_data(params)
#         return render(request, self.template_name, {'signature': signature, 'data': data})


@method_decorator(csrf_exempt, name='dispatch')
class PayCallbackView(View):
    def post(self, request, *args, **kwargs):
        liqpay = LiqPay(PUBLIC_KEY, PRIVATE_KEY)
        data = request.POST.get('data')
        signature = request.POST.get('signature')
        sign = liqpay.str_to_sign(PRIVATE_KEY + data + PRIVATE_KEY)
        if sign == signature:
            print('callback is valid')
        response = liqpay.decode_data_from_str(data)
        print('callback data', response)
        return HttpResponse()




# liqpay = LiqPay(PUBLIC_KEY, PRIVATE_KEY)
# html = liqpay.cnb_form({
#     'action': 'pay',
#     'amount': '1',
#     'currency': 'USD',
#     'description': 'description text',
#     'order_id': 'order_id_1',
#     'version': '3'
# })


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    # store transaction details inside payment model
    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    # move the cart items to order product table
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

        # reduce the quantity of the sold products
        product = Product.objects.filter(id=item.product_id)
        product.stock -= item.quantity
        product.save()


    # clear the cart
    CartItem.objects.filter(user=request.user).delete()

    # send order received email to customer
    mail_subject = 'Thank you for your order!'
    message = render_to_string(f'orders/order_received_email.html', {
        'user': request.user,
        'order': order,
    })
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    # send order number and transaction id back to sendData method via JsonResponse
    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }
    return JsonResponse(data)


    
    return render(request, 'orders/payments.html')


def place_order(request, total=0, quantity=0):
    current_user = request.user

    # if the cart count is less than or equal to 0, then redirect back to shop page
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total = (cart_item.product.price * cart_item.quantity)
        quantity = cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        # get the form values
        form = OrderForm(request.POST)
        if form.is_valid():
            # store all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }

            # liqpay = LiqPay(PUBLIC_KEY, PRIVATE_KEY)
            # context = liqpay.cnb_form({
            #     'action': 'pay',
            #     'amount': grand_total,
            #     'currency': 'USD',
            #     'description': 'description text',
            #     'order_id': order,
            #     'version': '3'
            # })

            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=transID)
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')