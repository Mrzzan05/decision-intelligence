from django import forms

from journal.models import DecisionEntry


class DecisionEntryForm(forms.ModelForm):
    class Meta:
        model = DecisionEntry
        fields = ["rationale", "satisfaction_rating"]
        widgets = {
            "rationale": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Explain why this product best matched your weighted criteria...",
                }
            ),
            "satisfaction_rating": forms.NumberInput(
                attrs={"min": 1, "max": 10, "placeholder": "1 - 10 (Optional)"}
            ),
        }

    def clean_rationale(self) -> str:
        rationale = (self.cleaned_data.get("rationale") or "").strip()
        if not rationale:
            raise forms.ValidationError("Please provide a rationale for your decision.")
        return rationale