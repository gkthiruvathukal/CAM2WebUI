from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from cam2webui.settings import EMAIL_HOST_USER, MANAGER_EMAIL
from email_system.forms import MailForm, ContactForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mass_mail, send_mail
import os
import json
import urllib
import sys
from django.conf import settings

@staff_member_required
def admin_send_email(request):
    # obtain user id list from session, or none
    user_selected = request.session.get('user_id_selected', None)
    # get a list of User objects
    user_info=[]
    if user_selected is not None:
        for i in user_selected:
            obj=User.objects.get(id=i)
            obj_info=[obj.is_staff, obj.username, obj.email, obj.first_name, obj.last_name, obj.date_joined]
            user_info.append(obj_info)

    if request.method == 'POST':
        form = MailForm(request.POST)
        if form.is_valid():
            # get admin input
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            email = form.cleaned_data['email']
            email_all_users = form.cleaned_data['email_all_users']# option for email all users

            current_site = get_current_site(request)  # will be used in templates
            try:
                if email_all_users: # if ture, send email to all users
                    all_users = User.objects.all() # For iteration of "email all users"
                    mass_email = []
                    for user in all_users:
                        if user.is_active:
                            username = user.username # will be used in template
                            template = render_to_string('email_system/admin_send_email_template.html', {
                                'username': username,
                                'message': message,
                                'domain': current_site.domain,
                            })
                            mass_email.append((
                                subject,
                                template,
                                EMAIL_HOST_USER,
                                [user.email],
                            ))
                    send_mass_mail(mass_email, fail_silently=False)
                else: # send email to users in the user id list, and address that the admin typed in
                    mass_email = []
                    # for user id list
                    if user_selected is not None:
                        for i in user_selected:
                            obj = User.objects.get(id=i)
                            if obj.email is not '':
                                username = obj.username  # will be used in template
                                template = render_to_string('email_system/admin_send_email_template.html', {
                                    'username': username,
                                    'message': message,
                                    'domain': current_site.domain,
                                })
                                mass_email.append((
                                    subject,
                                    template,
                                    EMAIL_HOST_USER,
                                    [obj.email],
                                ))
                    # for additional recipient
                    for e in email:
                        """ attach template one by one to make sure only one email is in the recipient_list,
                            if not, recipients in the same recipient_list will all see the other addresses
                            in the email messages’ “To:” field """
                        username = e # will be used in template
                        template = render_to_string('email_system/admin_send_email_template.html', {
                            'username': username,
                            'message': message,
                            'domain': current_site.domain,
                        })
                        mass_email.append((
                            subject,
                            template,
                            EMAIL_HOST_USER,
                            [e],
                        ))
                    send_mass_mail(mass_email, fail_silently=False)

                messages.success(request, 'Email successfully sent.')# success message
            except:
                messages.error(request, 'Email sent failed.')# error message

            return redirect('admin_send_email')
        else:
            messages.error(request, 'Email sent failed.')
    else:
        form = MailForm()
    return render(request, 'email_system/admin_send_email.html', {'form': form, 'users': user_info})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            recaptcha_response = request.POST.get('g-recaptcha-response')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            data = urllib.parse.urlencode(values).encode()
            req = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            if result['success']:

                #get info from form
                name = form.cleaned_data['name']
                from_email = form.cleaned_data['from_email']
                subject = '[CAM2 WebUI User Feedback] ' + form.cleaned_data['subject']
                message = form.cleaned_data['message']
                #add info to email template
                content = render_to_string('email_system/contact_email_template.html', {
                    'name': name,
                    'from_email': from_email,
                    'message': message,
                })
                send_mail(subject, content, EMAIL_HOST_USER, MANAGER_EMAIL)#email admin

                return redirect('email_sent')
            else:
                messages.error(request, 'Invalid reCAPTCHA. Please confirm you are not a robot and try again.')
                if 'test' in sys.argv:
                    sitekey = os.environ['RECAPTCHA_TEST_SITE_KEY']
                else:
                    sitekey = os.environ['RECAPTCHA_SITE_KEY']
        else:
            if 'test' in sys.argv:
                sitekey = os.environ['RECAPTCHA_TEST_SITE_KEY']
            else:
                sitekey = os.environ['RECAPTCHA_SITE_KEY']

    else:
        form = ContactForm()
        if 'test' in sys.argv:
            sitekey = os.environ['RECAPTCHA_TEST_SITE_KEY']
        else:
            sitekey = os.environ['RECAPTCHA_SITE_KEY']

    return render(request, "email_system/contact.html", {'form': form, 'sitekey': sitekey})

def email_sent(request):
    return render(request, 'email_system/email_sent.html')
