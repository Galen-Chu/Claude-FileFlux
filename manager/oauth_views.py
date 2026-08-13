"""
OAuth callback handlers for cloud drive authentication
"""
import requests
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urlencode

from .models import CloudStorageToken
from .services.cloud_manager import CloudDriveManager


@login_required
def oauth_callback(request):
    """
    Unified OAuth callback handler for all cloud providers
    Uses 'state' parameter to route to correct provider
    """
    # Check for error
    error = request.GET.get('error')
    if error:
        error_description = request.GET.get('error_description', 'Unknown error')
        messages.error(request, f'Authentication failed: {error_description}')
        return redirect('manager:profile')

    # Get authorization code and state
    code = request.GET.get('code')
    state = request.GET.get('state', '')

    if not code:
        messages.error(request, 'No authorization code received')
        return redirect('manager:profile')

    # Validate state against the session to prevent CSRF / forged callbacks.
    expected = request.session.pop('oauth_state', None)
    if not state or state != expected:
        messages.error(request, 'Invalid OAuth state. Please try connecting again.')
        return redirect('manager:profile')

    # Provider is encoded as the prefix before the nonce.
    provider = state.split(':', 1)[0]

    # Route based on state parameter
    if provider == 'onedrive':
        return _handle_onedrive_callback(request, code)
    elif provider == 'googledrive':
        return _handle_googledrive_callback(request, code)
    else:
        messages.error(request, f'Unknown OAuth provider: {provider}')
        return redirect('manager:profile')


def _handle_onedrive_callback(request, code):
    """Handle OneDrive OAuth callback"""
    try:
        # Exchange code for tokens
        token_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"

        data = {
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'scope': 'files.readwrite.all offline_access'
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            messages.error(request, f'Failed to exchange authorization code: {response.text}')
            return redirect('manager:profile')

        token_data = response.json()

        # Store tokens in database
        expires_in = token_data.get('expires_in', 3600)  # Default 1 hour

        CloudDriveManager.connect_drive(
            user=request.user,
            provider='onedrive',
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=expires_in
        )

        messages.success(request, 'OneDrive connected successfully! You can now access your files.')
        return redirect('manager:profile')

    except Exception as e:
        messages.error(request, f'Error connecting OneDrive: {str(e)}')
        return redirect('manager:profile')


def _handle_googledrive_callback(request, code):
    """Handle Google Drive OAuth callback"""
    try:
        # Exchange code for tokens
        token_url = 'https://oauth2.googleapis.com/token'

        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            messages.error(request, f'Failed to exchange authorization code: {response.text}')
            return redirect('manager:profile')

        token_data = response.json()

        # Store tokens in database
        expires_in = token_data.get('expires_in', 3600)  # Default 1 hour

        CloudDriveManager.connect_drive(
            user=request.user,
            provider='googledrive',
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=expires_in
        )

        messages.success(request, 'Google Drive connected successfully! You can now access your files.')
        return redirect('manager:profile')

    except Exception as e:
        messages.error(request, f'Error connecting Google Drive: {str(e)}')
        return redirect('manager:profile')


# Keep old function names for backward compatibility
@login_required
def onedrive_oauth_callback(request):
    """Legacy OneDrive callback - redirects to unified handler"""
    return oauth_callback(request)


@login_required
def googledrive_oauth_callback(request):
    """Legacy Google Drive callback - redirects to unified handler"""
    return oauth_callback(request)
