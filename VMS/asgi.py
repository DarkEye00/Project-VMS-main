"""
ASGI config for VMS project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import userauth.routing  # assuming the app with websocket is named 'user'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VMS.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            userauth.routing.websocket_urlpatterns
        )
    ),
})