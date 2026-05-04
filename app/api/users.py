from rest_framework import viewsets

from app.models import ChatUser
from app.serializers import ChatUserSerializer


class ChatUserViewSet(viewsets.ModelViewSet):
    queryset = ChatUser.objects.all()
    serializer_class = ChatUserSerializer