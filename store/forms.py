from django import forms

from store.models import ReviewRating


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']



    # rating = forms.ChoiceField(choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], widget=forms.Select(
    #     attrs={
    #         'class': 'form-control'
    #     }
    # ))
    # comment = forms.CharField(widget=forms.Textarea(attrs={
    #     'class': 'form-control'
    # }))