def auth_nav(request):
    user = request.user
    display_name = ""
    if user.is_authenticated:
        display_name = user.first_name or user.get_full_name() or user.email.split("@")[0]
    return {"nav_display_name": display_name}
