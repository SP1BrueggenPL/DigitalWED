from django import forms
from .models import KotlowniaFormularz


def _num(extra=None):
    attrs = {'class': 'form-control', 'step': '0.01'}
    if extra:
        attrs.update(extra)
    return forms.NumberInput(attrs=attrs)


class EtapTechnicznyForm(forms.ModelForm):
    class Meta:
        model = KotlowniaFormularz
        fields = [
            'data', 'godzina',
            'woda_socjalna_m3', 'woda_produkcja_m3',
            'olej_poziom_cm', 'olej_licznik_litry',
            'gaz_cisnienie_1', 'gaz_wypelnienie_1',
            'gaz_cisnienie_2', 'gaz_wypelnienie_2',
            'gaz_cisnienie_3', 'gaz_wypelnienie_3',
            'gaz_cisnienie_4', 'gaz_wypelnienie_4',
            'gaz_cisnienie_5', 'gaz_wypelnienie_5',
            'gaz_cisnienie_6', 'gaz_wypelnienie_6',
        ] + [f'b{i}_wartosc' for i in range(1, 16)] + [f'b{i}_uwagi' for i in range(1, 16)]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'godzina': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, 7):
            self.fields[f'gaz_cisnienie_{i}'].widget = _num()
            self.fields[f'gaz_wypelnienie_{i}'].widget = _num()
        for f in ['woda_socjalna_m3', 'woda_produkcja_m3', 'olej_poziom_cm', 'olej_licznik_litry']:
            self.fields[f].widget = _num()
        for i in range(1, 16):
            self.fields[f'b{i}_wartosc'].widget = forms.TextInput(attrs={'class': 'form-control'})
            self.fields[f'b{i}_uwagi'].widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 2})


class EtapLaboratoriumForm(forms.ModelForm):
    class Meta:
        model = KotlowniaFormularz
        fields = [
            'lab_godzina',
            'wz_ph', 'wz_wapnioce_dh', 'wz_tlen_mg', 'wz_przewodnosc', 'wz_temperatura', 'wz_wyglad',
            'k_ph', 'k_wapnioce_dh', 'k_przewodnosc',
            'wk_ph', 'wk_wapnioce_dh', 'wk_przewodnosc', 'wk_wyglad',
            'wu_ph', 'wu_wapnioce_dh', 'wu_przewodnosc',
        ]
        widgets = {
            'lab_godzina': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'wz_wyglad': forms.RadioSelect(),
            'wk_wyglad': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dec_fields = [
            'wz_ph', 'wz_wapnioce_dh', 'wz_tlen_mg', 'wz_przewodnosc', 'wz_temperatura',
            'k_ph', 'k_wapnioce_dh', 'k_przewodnosc',
            'wk_ph', 'wk_wapnioce_dh', 'wk_przewodnosc',
            'wu_ph', 'wu_wapnioce_dh', 'wu_przewodnosc',
        ]
        for f in dec_fields:
            self.fields[f].widget = _num()
