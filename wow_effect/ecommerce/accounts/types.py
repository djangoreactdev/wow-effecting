from django.db import models
from graphene_django.types import DjangoObjectType
from .models import User, Profile


class ProfileType(DjangoObjectType):
    class Meta:
        model = Profile
        

class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ['password']



class UserTypeFull(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "email",) 

    def resolve_id(self, info):
        return str(self.id)

    def as_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            # Add other fields as needed
        }