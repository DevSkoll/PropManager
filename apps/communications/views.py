from django.contrib import messages as django_messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import User
from apps.core.decorators import admin_required, tenant_required

from .forms import AnnouncementForm, MessageForm, ThreadCreateForm
from .models import Announcement, Message, MessageThread, Notification


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


@admin_required
def admin_thread_list(request):
    threads = (
        MessageThread.objects.prefetch_related("participants", "messages")
        .all()
        .order_by("-updated_at")
    )
    return render(request, "communications/admin_thread_list.html", {"threads": threads})


@admin_required
def admin_thread_detail(request, pk):
    thread = get_object_or_404(
        MessageThread.objects.prefetch_related("participants", "messages__sender"), pk=pk
    )

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.thread = thread
            msg.sender = request.user
            msg.save()
            thread.updated_at = timezone.now()
            thread.save(update_fields=["updated_at"])
            django_messages.success(request, "Reply sent.")
            return redirect("communications_admin:thread_detail", pk=thread.pk)
    else:
        form = MessageForm()

    thread_messages = thread.messages.select_related("sender").order_by("created_at")
    return render(
        request,
        "communications/admin_thread_detail.html",
        {"thread": thread, "thread_messages": thread_messages, "form": form},
    )


@admin_required
def admin_thread_create(request):
    if request.method == "POST":
        form = ThreadCreateForm(request.POST, user=request.user)
        if form.is_valid():
            thread = MessageThread.objects.create(subject=form.cleaned_data["subject"])
            # Add admin + selected participants
            participants = list(form.cleaned_data["participants"])
            thread.participants.add(request.user, *participants)
            Message.objects.create(
                thread=thread,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            django_messages.success(request, "Thread created.")
            return redirect("communications_admin:thread_detail", pk=thread.pk)
    else:
        form = ThreadCreateForm(user=request.user)

    return render(request, "communications/admin_thread_create.html", {"form": form})


@admin_required
def admin_announcement_list(request):
    announcements = Announcement.objects.select_related("property", "author").order_by(
        "-created_at"
    )
    return render(
        request,
        "communications/admin_announcement_list.html",
        {"announcements": announcements},
    )


@admin_required
def admin_announcement_create(request):
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.created_by = request.user
            if announcement.is_published and not announcement.published_at:
                announcement.published_at = timezone.now()
            announcement.save()
            django_messages.success(request, "Announcement created.")
            return redirect("communications_admin:announcement_list")
    else:
        form = AnnouncementForm()

    return render(
        request,
        "communications/admin_announcement_create.html",
        {"form": form, "editing": False},
    )


@admin_required
def admin_announcement_edit(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.updated_by = request.user
            if announcement.is_published and not announcement.published_at:
                announcement.published_at = timezone.now()
            announcement.save()
            django_messages.success(request, "Announcement updated.")
            return redirect("communications_admin:announcement_list")
    else:
        form = AnnouncementForm(instance=announcement)

    return render(
        request,
        "communications/admin_announcement_create.html",
        {"form": form, "editing": True, "announcement": announcement},
    )


# ---------------------------------------------------------------------------
# Tenant views
# ---------------------------------------------------------------------------


@tenant_required
def tenant_thread_list(request):
    threads = (
        MessageThread.objects.filter(participants=request.user)
        .prefetch_related("participants", "messages__sender")
        .order_by("-updated_at")
    )

    # Annotate with unread count for the current user
    thread_data = []
    for thread in threads:
        unread = thread.messages.filter(is_read=False).exclude(sender=request.user).count()
        thread_data.append({"thread": thread, "unread": unread})

    return render(
        request,
        "communications/tenant_thread_list.html",
        {"thread_data": thread_data},
    )


@tenant_required
def tenant_thread_detail(request, pk):
    thread = get_object_or_404(
        MessageThread.objects.filter(participants=request.user).prefetch_related(
            "participants", "messages__sender"
        ),
        pk=pk,
    )

    # Mark messages from others as read
    thread.messages.filter(is_read=False).exclude(sender=request.user).update(
        is_read=True, read_at=timezone.now()
    )

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.thread = thread
            msg.sender = request.user
            msg.save()
            thread.updated_at = timezone.now()
            thread.save(update_fields=["updated_at"])
            django_messages.success(request, "Message sent.")
            return redirect("communications_tenant:thread_detail", pk=thread.pk)
    else:
        form = MessageForm()

    thread_messages = thread.messages.select_related("sender").order_by("created_at")
    return render(
        request,
        "communications/tenant_thread_detail.html",
        {"thread": thread, "thread_messages": thread_messages, "form": form},
    )


@tenant_required
def tenant_thread_create(request):
    if request.method == "POST":
        form = ThreadCreateForm(request.POST, user=request.user)
        if form.is_valid():
            thread = MessageThread.objects.create(subject=form.cleaned_data["subject"])
            # Add tenant + all admins/staff
            admins = User.objects.filter(role__in=["admin", "staff"], is_active=True)
            thread.participants.add(request.user, *admins)
            Message.objects.create(
                thread=thread,
                sender=request.user,
                body=form.cleaned_data["body"],
            )
            django_messages.success(request, "Message sent to management.")
            return redirect("communications_tenant:thread_detail", pk=thread.pk)
    else:
        form = ThreadCreateForm(user=request.user)

    return render(request, "communications/tenant_thread_create.html", {"form": form})


@tenant_required
def tenant_notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")

    # HTMX: mark a single notification as read
    if request.method == "POST" and request.headers.get("HX-Request"):
        notification_id = request.POST.get("notification_id")
        if notification_id:
            Notification.objects.filter(
                pk=notification_id, recipient=request.user, is_read=False
            ).update(is_read=True, read_at=timezone.now())
            # Return updated notification item partial
            notification = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
            return render(
                request,
                "communications/_notification_item.html",
                {"notification": notification},
            )

    return render(
        request,
        "communications/tenant_notification_list.html",
        {"notifications": notifications},
    )
