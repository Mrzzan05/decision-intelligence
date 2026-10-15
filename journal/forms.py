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
            "rationale": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Explain why this product best matched your weighted criteria...",
                }
            ),
            "expected_outcome": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Pre-purchase expectation: What do you expect this product to achieve?",
                }
            ),
            "expected_rating": forms.NumberInput(
                attrs={"min": 1, "max": 10, "placeholder": "1 - 10 (Expected)"}
            ),
            "actual_experience": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Post-purchase reality: How did it actually perform over time?",
                }
            ),
            "satisfaction_rating": forms.NumberInput(
                attrs={"min": 1, "max": 10, "placeholder": "1 - 10 (Actual Outcome)"}
            ),
        }

    def clean_rationale(self) -> str:
        rationale = (self.cleaned_data.get("rationale") or "").strip()
        if not rationale:
            raise forms.ValidationError("Please provide a rationale for your decision.")
        return rationale
