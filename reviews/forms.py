from django import forms

from reviews.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["overall_rating", "pros", "cons", "comment"]
        widgets = {
            "overall_rating": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "pros": forms.Textarea(attrs={"rows": 2, "placeholder": "Key strengths experienced..."}),
            "cons": forms.Textarea(attrs={"rows": 2, "placeholder": "Notable trade-offs or weaknesses..."}),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Detailed evaluation..."}),
        }
