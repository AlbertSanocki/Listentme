"""Views for playlistapp apllication"""
from django.shortcuts import render
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from .spotifyService.util import get_current_user, create_a_playlist, get_current_users_playlists
from .forms import NewPlaylistDataForm, ArtistForm

def home(request):
    """Homepage view"""
    current_user = get_current_user(request.session.session_key)
    users_playlists = get_current_users_playlists(request.session.session_key)
    context = {
        'current_user': current_user,
        'users_playlists': users_playlists
    }
    return render(request, 'playlistapp/home.html', context)

def create(request):
    """Create page View"""
    current_user = get_current_user(request.session.session_key)
    ArtistFormSet = formset_factory(ArtistForm, extra=0)
    if request.method == 'POST':
        new_playlist_data_form = NewPlaylistDataForm(request.POST or None, request.FILES or None)
        artist_formset = ArtistFormSet(request.POST or None)
        if all([new_playlist_data_form.is_valid(), artist_formset.is_valid()]):
            form_data = {
                'img': new_playlist_data_form.cleaned_data['img'],
                'name': new_playlist_data_form.cleaned_data['name'],
                'description': new_playlist_data_form.cleaned_data['description'],
                'public': new_playlist_data_form.cleaned_data['public'],
                'artists': [form.cleaned_data['artist'] for form in artist_formset]
            }
            create_a_playlist(request.session.session_key, form_data)
            return HttpResponseRedirect('/create')
    else:
        new_playlist_data_form = NewPlaylistDataForm(request.POST)
        artist_formset = ArtistFormSet(request.POST or None)
    context = {
        'current_user':current_user,
        'new_playlist_data_form':new_playlist_data_form,
        'artist_formset': artist_formset
    }
    return render(request, 'playlistapp/create.html', context)

def view(request):
    """View page View"""
    current_user = get_current_user(request.session.session_key)
    context = {
    'current_user': current_user
    }

    return render(request, 'playlistapp/view.html', context)
