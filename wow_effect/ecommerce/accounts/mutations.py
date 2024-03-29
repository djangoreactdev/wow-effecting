from ..accounts.models import Profile
import graphene
import graphql_jwt
from graphene.types.generic import GenericScalar
from graphql_jwt.decorators import login_required
from graphene_file_upload.scalars import Upload
from graphql_jwt.shortcuts import get_token

from wow_effect.users.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


from .types import UserType
from .utils import get_from_redis, token_delete_to_redis
from .tasks import task_send_register_email, task_send_change_email, task_send_reset_password_email

from django_graphql_jwt.utils import jwt_refresh_token_for_user


class AccountInput(graphene.InputObjectType):
    username = graphene.String(required=True)
    email = graphene.String(required=True)
    password = graphene.String(required=True)
    first_name = graphene.String()
    last_name = graphene.String()


# class AccountLogin(graphene.Mutation):
#     class Arguments:
#         email = graphene.String()
#         username = graphene.String()
#         password = graphene.String()

#     response = GenericScalar()

#     def mutate(parent, info, username, email, password):
#         try:
#             user = User.objects.get(username=username)
#             if user.check_password(password):
#                 return AccountLogin(response={"status": "success", "message": "login success."})
#             else:
#                 return AccountLogin(response={"status": "error", "message": "Your password is invalid."})
#         except User.DoesNotExist:
#             try:
#                 user = User.objects.get(email=email)
#                 if user.check_password(password):
#                     user_data = serializers.serialize('json', [user])
#                     return AccountLogin( response={"status": "success", "message": "login success.",
#                                                    "token":  get_token(user), "user": user_data})
#                 else:
#                     return AccountLogin(response={"status": "error", "message": "Your password is invalid."})
#             except User.DoesNotExist:
#                 return AccountLogin(response={"status": "error", "message": "Your email is invalid."})


class ChangeEmail(graphene.Mutation):
    class Arguments:
        email = graphene.String()

    response = GenericScalar()

    @login_required
    def mutate(parent, info, email):
        try:
            User.objects.get(email=email)
            return ChangeEmail(response={"status": "error", "message": "Email address already taken."})

        except User.DoesNotExist:
            user = info.context.user
            user.email = email
            user.is_active = False
            user.save()
            task_send_change_email.delay(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            return ChangeEmail(response={"status": "success", "message": "send email ."})


class VerifyEmail(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        email = graphene.String(required=True)

    response = GenericScalar()

    def mutate(parent, info, token, email):
        try:
            user = User.objects.get(email=email)
            token_from_redis = get_from_redis(user.id, "change_email")

            if not token_from_redis:
                return VerifyEmail(response={"status": "error", "message": "Wrong/Expired Token!"})

            if token != token_from_redis.decode("UTF-8"):
                return VerifyEmail(response={"status": "error", "message": "Wrong/Expired Token!"})

            user.is_active = True
            user.save()
            token_delete_to_redis(user.id, "change_email")
            return VerifyEmail(response={"status": "success", "message": "verify email."})

        except User.DoesNotExist:
            return VerifyEmail(response={"status": "error", "message": "Wrong/Expired Token!"})


class ResetPassword(graphene.Mutation):
    class Arguments:
        email = graphene.String()

    response = GenericScalar()

    def mutate(parent, info, email):
        try:
            user = User.objects.get(email=email)
            task_send_reset_password_email.delay(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            return ResetPassword(response={"status": "success", "message": "send email."})

        except User.DoesNotExist:
            return ResetPassword(response={"status": "error", "message": "Email dose not exists."})


class VerifyPassword(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        email = graphene.String(required=True)
        new_password = graphene.String(required=True)

    response = GenericScalar()

    def mutate(parent, info, token, email, new_password):
        try:
            user = User.objects.get(email=email)
            token_from_redis = get_from_redis(user.id, "reset_password")

            if not token_from_redis:
                return VerifyPassword(response={"status": "error", "message": "Wrong/Expired Token!."})

            if token != token_from_redis.decode("UTF-8"):
                return VerifyPassword(response={"status": "error", "message": "Wrong/Expired Token!."})

            user.set_password(new_password)
            user.save()
            token_delete_to_redis(user.id, "reset_password")
            return VerifyPassword(response={"status": "success", "message": "verify password."})

        except User.DoesNotExist:
            return VerifyPassword(response={"status": "error", "message": "Wrong/Expired Token!."})


class ChangePassword(graphene.Mutation):
    class Arguments:
        old_password = graphene.String()
        new_password = graphene.String()

    response = GenericScalar()

    @login_required
    def mutate(parent, info, old_password, new_password):
        user = info.context.user
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return ChangePassword(response={"status": "success", "message": "change password."})
        else:
            return ChangePassword(response={"status": "error", "message": "Your old password is invalid."})


class CreateAccount(graphene.Mutation):
    class Arguments:
        input = AccountInput(required=True)

    user = graphene.Field(UserType)
    response = GenericScalar()

    def mutate(parent, info, input):
        user = None
        try:
            validate_email(input.email)
            try:
                user_exists = User.objects.get(email=input.email)

                if user_exists is None:
                    user = User.objects.create_user(
                        username=input.username,
                        email=input.email,
                        password=input.password,
                        is_active=False,
                        first_name=input.first_name,
                        last_name=input.last_name,
                    )
                elif user_exists.is_active:
                    return CreateAccount(response={"status": "error", "message": "Duplicate user."})
                else:
                    user = user_exists

            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=input.username,
                    email=input.email,
                    password=input.password,
                    is_active=False,
                    first_name=input.first_name,
                    last_name=input.last_name,
                )

            task_send_register_email.delay(
                id=user.id,
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            token = get_token(user)
            print(token)
            return CreateAccount(
                response={
                    "status": "success",
                    "message": "create user.",
                    "token": token,
                }
            )

        except ValidationError:
            return CreateAccount(
                response={"status": "error", "message": "Enter a valid e-mail address."},
            )


class ActivateAccount(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        email = graphene.String(required=True)

    response = GenericScalar()

    def mutate(parent, info, token, email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return ActivateAccount(response={"status": "error", "message": "Wrong/Expired Token!."})

        token_from_redis = get_from_redis(user.id, "register")
        if not token_from_redis:
            return ActivateAccount(response={"status": "error", "message": "Wrong/Expired Token!."})

        if token != token_from_redis.decode("UTF-8"):
            return ActivateAccount(response={"status": "error", "message": "Wrong/Expired Token!."})

        user.is_active = True
        user.save()
        token_delete_to_redis(user.id, "register")
        return ActivateAccount(response={"status": "success", "message": "active account."})


class UpdateAccount(graphene.Mutation):
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        username = graphene.String()

    response = GenericScalar()
    user = graphene.Field(UserType)

    @login_required
    def mutate(parent, info, first_name, last_name, username):
        user = User.objects.get(id=info.context.user.id)
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.username = username or user.username
        user.save()
        return UpdateAccount(user=user, response={"status": "success", "message": "update account."})


class UpdateProfile(graphene.Mutation):
    class Arguments:
        bio = graphene.String(required=False)
        image = Upload(required=False)
        age = graphene.Int(required=False)

    response = GenericScalar()

    @login_required
    def mutate(parent, info, bio, image, age):
        user = info.context.user
        try:
            profile = user.profile

        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)

        profile.bio = bio or profile.bio
        profile.image = image or profile.image
        profile.age = age or profile.age
        profile.save()
        return UpdateProfile(response={"status": "success", "message": "update profile."})


class AccountsMutation(graphene.ObjectType):
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()

    def resolve_refreshToken(self, info, **kwargs):
        """
        Returns the refresh token for the user.
        """
        user = info.context.user
        refresh_token = jwt_refresh_token_for_user(user)
        return {"refreshToken": refresh_token}

    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    revoke_token = graphql_jwt.Revoke.Field()

    # account_login = AccountLogin.Field()
    create_account = CreateAccount.Field()
    activate_account = ActivateAccount.Field()
    update_account = UpdateAccount.Field()

    change_password = ChangePassword.Field()
    reset_password = ResetPassword.Field()
    verify_password = VerifyPassword.Field()

    change_email = ChangeEmail.Field()
    verify_email = VerifyEmail.Field()

    update_profile = UpdateProfile.Field()
