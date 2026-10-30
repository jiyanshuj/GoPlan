from django import forms

CRITERIA_CHOICES = [
    ('cost', 'Cost / Budget (Lowest Price)'),
    ('time', 'Travel Time (Fastest Journey)'),
    ('co2', 'Carbon Footprint (Lowest CO₂ Emissions)'),
    ('comfort', 'Comfort & Convenience (Best Experience)'),
]

class TripForm(forms.Form):
    current_location = forms.CharField(
        max_length=255,
        label='Current Location',
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'current',
            'class': 'input',
            'placeholder': 'Enter your location'
        })
    )
    destination = forms.CharField(
        max_length=255,
        label='Destination',
        required=True,
        widget=forms.TextInput(attrs={
            'id': 'destination',
            'class': 'input',
            'placeholder': 'Enter destination'
        })
    )
    start_date = forms.DateField(
        required=False,
        label='Starting Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'start-date',
            'class': 'input'
        })
    )
    end_date = forms.DateField(
        required=False,
        label='Ending Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'id': 'end-date',
            'class': 'input'
        })
    )
    people = forms.IntegerField(
        min_value=1,
        required=False,
        initial=1,
        label='Number of People',
        widget=forms.NumberInput(attrs={
            'id': 'people',
            'class': 'input',
            'min': '1',
            'placeholder': 'Enter number of travelers'
        })
    )
    budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label='Budget',
        required=False,
        widget=forms.NumberInput(attrs={
            'id': 'budget',
            'class': 'input',
            'min': '0',
            'placeholder': 'Enter budget'
        })
    )

    # Best-Worst Method (BWM) User Preference Inputs
    most_important = forms.ChoiceField(
        choices=CRITERIA_CHOICES,
        required=False,
        initial='cost',
        label='Most Important Factor'
    )
    least_important = forms.ChoiceField(
        choices=CRITERIA_CHOICES,
        required=False,
        initial='co2',
        label='Least Important Factor'
    )
