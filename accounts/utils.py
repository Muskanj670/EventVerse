from .models import UserProfile


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        return 'admin'
    return UserProfile.objects.filter(user=user).values_list('role', flat=True).first() or UserProfile.Role.ATTENDEE


def is_organizer_or_admin(user):
    role = get_user_role(user)
    return role in {'organizer', 'admin'}
