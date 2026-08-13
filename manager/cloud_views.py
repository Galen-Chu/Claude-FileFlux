"""
Cloud drive OAuth views
"""
import secrets

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from urllib.parse import urlencode

from .services.cloud_manager import CloudDriveManager
from .models import CloudStorageToken


def _make_oauth_state(request, provider):
    """
    Create a CSRF-protecting state token that ties the OAuth round-trip to
    this session. The provider is encoded as the prefix before the nonce.
    """
    state = f'{provider}:{secrets.token_urlsafe(32)}'
    request.session['oauth_state'] = state
    return state


@login_required
def connect_onedrive(request):
    """
    Initiate OneDrive OAuth connection
    Redirects to Microsoft login page
    """
    try:
        state = _make_oauth_state(request, 'onedrive')
        # Build Microsoft OAuth URL
        params = {
            'client_id': settings.MS_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'scope': 'files.readwrite.all offline_access',
            'response_mode': 'query',
            'state': state,
        }

        auth_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/authorize?{urlencode(params)}"

        # Redirect user to Microsoft login
        return redirect(auth_url)

    except Exception as e:
        messages.error(request, f'Failed to initiate OneDrive connection: {str(e)}')
        return redirect('manager:profile')


@login_required
def connect_googledrive(request):
    """
    Initiate Google Drive OAuth connection
    Redirects to Google login page
    """
    try:
        state = _make_oauth_state(request, 'googledrive')
        # Build Google OAuth URL
        params = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/drive.file',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        # Redirect user to Google login
        return redirect(auth_url)

    except Exception as e:
        messages.error(request, f'Failed to initiate Google Drive connection: {str(e)}')
        return redirect('manager:profile')


@login_required
@require_POST
def disconnect_drive(request, provider):
    """
    Disconnect a cloud drive
    """
    try:
        success = CloudDriveManager.disconnect_drive(request.user, provider)

        if success:
            messages.success(request, f'{provider.title()} disconnected successfully!')
        else:
            messages.warning(request, f'{provider.title()} was not connected.')

    except Exception as e:
        messages.error(request, f'Failed to disconnect {provider}: {str(e)}')

    return redirect('manager:profile')


@login_required
def cloud_status(request):
    """
    Get cloud drive connection status (API endpoint)
    """
    drives = CloudDriveManager.get_connected_drives(request.user)

    return JsonResponse({
        'drives': drives,
        'total': len(drives)
    })
