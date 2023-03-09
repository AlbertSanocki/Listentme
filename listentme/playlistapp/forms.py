"""Forms for collecting user preferences"""
from django import forms

class NewPlaylistDataForm(forms.Form):
    """New Playlist preferences"""
    img = forms.ImageField(label='Img', required=False)
    name = forms.CharField(
        label='Name',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Playlist Name','autocomplete': 'off'})
    )
    description = forms.CharField(
        label='Desciprion',
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Desciprion','autocomplete': 'off'})
    )
    public = forms.BooleanField(required=False)

class ArtistForm(forms.Form):
    """Artist information"""
    artist = forms.CharField(
        label='',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off'})
    )
