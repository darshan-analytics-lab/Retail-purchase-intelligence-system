from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, auth
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render
from account.models import Profile


def signup(request):
    content = {'title': 'Signup'}
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        content['form_data'] = {
            'full_name': full_name,
            'username': username,
            'email': email,
            'mobile': mobile,
        }

        if not full_name or not username or not email or not password or not confirm_password:
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'signup.html', content)

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html', content)

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Username already exists. Please choose a different one.')
            return render(request, 'signup.html', content)

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Email already exists. Please use a different email.')
            return render(request, 'signup.html', content)

        if mobile and Profile.objects.filter(mobile=mobile).exists():
            messages.error(request, 'Mobile number already exists. Please use a different number.')
            return render(request, 'signup.html', content)

        if mobile and (not mobile.isdigit() or len(mobile) != 10):
            messages.error(request, 'Please enter a valid 10 digit mobile number.')
            return render(request, 'signup.html', content)

        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'signup.html', content)

        name_parts = full_name.split()
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.save()
            if mobile:
                Profile.objects.create(mobile=mobile, user=user)
            messages.success(request, "Signup successfully. You can login now.")
            return HttpResponseRedirect(reverse('login'))
        except IntegrityError:
            messages.error(request, "Account details already exist. Please check username, email, or mobile.")
            return render(request, 'signup.html', content)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'signup.html', content)
    return render(request, 'signup.html', content)


def login(request):
    content = {'title': 'Login'}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')
        content['form_data'] = {'username': username, 'remember_me': remember_me}

        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'login.html', content)

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            return HttpResponseRedirect(reverse('index'))
        else:
            messages.error(request, "Invalid credentials.")
            return render(request, 'login.html', content)
    return render(request, 'login.html', content)


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('login'))


@login_required(login_url='login')
def profile(request):
    try:
        profile_obj = request.user.profile
    except Profile.DoesNotExist:
        profile_obj = None

    content = {
        'title': 'Profile',
        'profile': profile_obj,
    }
    return render(request, 'profile.html', content)
