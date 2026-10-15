from django import forms

from journal.models import DecisionEntry


class DecisionEntryForm(forms.ModelForm):
    class Meta:
        model = DecisionEntry
        fields = [
            "rationale",
            "expected_outcome",
            "expected_rating",
            "actual_experience",
            "satisfaction_rating",
        ]
        widgets = {
            "rationale": forms.Textarea(attrs={"rows": 3}),
            "expected_outcome": forms.Textarea(attrs={"rows": 2}),
            "expected_rating": forms.NumberInput(attrs={"min": 1, "max": 10}),
            "actual_experience": forms.Textarea(attrs={"rows": 2}),
            "satisfaction_rating": forms.NumberInput(attrs={"min": 1, "max": 10}),
        }

    def clean_rationale(self) -> str:
        rationale = (self.cleaned_data.get("rationale") or "").strip()
        if not rationale:
            raise forms.ValidationError("Please provide a rationale for your decision.")
        return rationale
