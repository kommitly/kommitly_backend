from django.contrib.auth.models import AbstractUser, BaseUserManager
import logging

logger = logging.getLogger(__name__)
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, first_name, last_name, password=None, timezone='UTC',**extra_fields ):
        """print(f"User found: {target_user.username}. Last active: {target_user.last_active}")
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)

        logger.debug(f"Creating user with timezone: {timezone}")

        user = self.model(email=email, first_name=first_name, last_name=last_name,  timezone=timezone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None,  timezone='UTC',**extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, first_name,last_name, password, timezone, **extra_fields)
