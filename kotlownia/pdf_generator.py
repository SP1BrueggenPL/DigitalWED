# -*- coding: utf-8 -*-
"""fpdf2-based PDF generator for Kotłownia CD-00001498-2 form."""
import io
import math
import base64
from fpdf import FPDF, XPos, YPos

ARIAL      = r'C:\Windows\Fonts\arial.ttf'
ARIAL_BOLD = r'C:\Windows\Fonts\arialbd.ttf'

MARGIN_LR   = 8
MARGIN_TB   = 6
EFFECTIVE_W = 210 - 2 * MARGIN_LR  # 194 mm

ROW_H  = 3.8
HDR_H  = 4.5
SEC_H  = 4.0

FS       = 6.5
FS_SMALL = 5.5

HEADER_BG = (240, 240, 240)
DARK_RED  = (102, 28, 49)


def _v(val):
    return '' if val is None else str(val)


class KotlowniaPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.add_font('Arial', '',  ARIAL)
        self.add_font('Arial', 'B', ARIAL_BOLD)
        self.set_margins(MARGIN_LR, MARGIN_TB)
        self.set_auto_page_break(False)
        self.add_page()

    # ── primitives ────────────────────────────────────────────────────────

    def _f(self, bold=False, size=FS):
        self.set_font('Arial', 'B' if bold else '', size)

    def _advance(self, h):
        """Move cursor to left margin, h mm lower."""
        self.set_xy(MARGIN_LR, self.get_y() + h)

    def _th(self, w, h, txt, align='L'):
        self._f(bold=True, size=FS_SMALL)
        self.set_fill_color(*HEADER_BG)
        self.cell(w, h, txt, border=1, align=align, fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.TOP)

    def _td(self, w, h, txt, align='L', bold=False, size=FS):
        self._f(bold=bold, size=size)
        self.cell(w, h, txt, border=1, align=align,
                  new_x=XPos.RIGHT, new_y=YPos.TOP)

    def _calc_lines(self, txt, w):
        """Number of wrapped lines for txt in a cell of width w mm."""
        if not txt:
            return 1
        self._f(size=FS)
        return max(1, math.ceil(self.get_string_width(txt) / (w - 1)))

    def _sec(self, title):
        self._f(bold=True, size=FS)
        self.set_fill_color(*HEADER_BG)
        self.cell(EFFECTIVE_W, SEC_H, title, border=1, fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── document sections ─────────────────────────────────────────────────

    def build_header(self, obj, now_str):
        logo_w  = 22
        meta_w  = 38
        title_w = EFFECTIVE_W - logo_w - meta_w
        h       = 11
        x0 = MARGIN_LR
        y0 = self.get_y()

        # Logo
        self.rect(x0, y0, logo_w, h)
        self._f(bold=True, size=11)
        self.set_text_color(*DARK_RED)
        self.set_xy(x0, y0 + (h - 5) / 2)
        self.cell(logo_w, 5, 'Brüggen', align='C',
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(0, 0, 0)

        # Title
        self.rect(x0 + logo_w, y0, title_w, h)
        self._f(bold=True, size=8.5)
        self.set_xy(x0 + logo_w + 1, y0 + 1)
        self.cell(title_w - 2, 5, 'Nadzór nad kotłownią – formularz',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._f(bold=False, size=FS_SMALL)
        self.set_text_color(80, 80, 80)
        self.set_x(x0 + logo_w + 1)
        self.cell(title_w - 2, 3.5,
                  'CD-00001498-2   Formblatt / Formularz / Formulaire / Form',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)

        # Meta
        self.rect(x0 + logo_w + title_w, y0, meta_w, h)
        self._f(bold=False, size=FS_SMALL)
        self.set_xy(x0 + logo_w + title_w + 1, y0 + 1.5)
        self.cell(meta_w - 2, 3.5, f'Data wydruku: {now_str}', align='R',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(x0 + logo_w + title_w + 1)
        date_str = obj.data.strftime('%d.%m.%Y') if obj.data else ''
        self.cell(meta_w - 2, 3.5, f'Data formularza: {date_str}', align='R',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_xy(MARGIN_LR, y0 + h + 1)

    def build_dzial_techniczny(self, obj):
        tech_name = ''
        if obj.technician:
            tech_name = obj.technician.get_full_name() or obj.technician.username

        self._sec('DZIAŁ TECHNICZNY:')

        w1 = round(EFFECTIVE_W * 0.46, 2)
        w2 = round(EFFECTIVE_W * 0.27, 2)
        w3 = EFFECTIVE_W - w1 - w2
        h  = ROW_H + 2.5

        x0, y0 = MARGIN_LR, self.get_y()
        for col_x, col_w, label, value in [
            (x0,          w1, 'Imię i Nazwisko',  tech_name),
            (x0 + w1,     w2, 'Data',              obj.data.strftime('%d.%m.%Y') if obj.data else ''),
            (x0 + w1 + w2, w3, 'Godzina',          obj.godzina.strftime('%H:%M') if obj.godzina else ''),
        ]:
            self.rect(col_x, y0, col_w, h)
            self._f(bold=True, size=FS_SMALL)
            self.set_xy(col_x + 1, y0 + 0.5)
            self.cell(col_w - 2, 3, label)
            self._f(bold=False, size=7)
            self.set_xy(col_x + 1, y0 + 3.5)
            self.cell(col_w - 2, 3, value)

        self.set_xy(MARGIN_LR, y0 + h + 0.5)

    def build_section_a(self, obj):
        self._sec('A. Kontrola stanu zapasów surowców technicznych')

        w4 = EFFECTIVE_W / 4

        # Water/oil merged header
        self._f(bold=True, size=FS_SMALL)
        self.set_fill_color(*HEADER_BG)
        self.cell(w4 * 2, HDR_H, 'Woda miejska', border=1, align='C', fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(w4 * 2, HDR_H, 'Olej opałowy', border=1, align='C', fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self._th(w4, HDR_H, 'Pomieszczenie socjalne [ m³ ]')
        self._th(w4, HDR_H, 'Produkcja [ m³ ]')
        self._th(w4, HDR_H, 'Poziom zbiornika [ cm ]')
        self._th(w4, HDR_H, 'Licznik oleju [ litry ]')
        self._advance(HDR_H)

        self._td(w4, ROW_H, _v(obj.woda_socjalna_m3))
        self._td(w4, ROW_H, _v(obj.woda_produkcja_m3))
        self._td(w4, ROW_H, _v(obj.olej_poziom_cm))
        self._td(w4, ROW_H, _v(obj.olej_licznik_litry))
        self._advance(ROW_H + 0.8)

        # Gas table
        lbl_w = 28
        num_w = (EFFECTIVE_W - lbl_w) / 6

        self._f(bold=True, size=FS_SMALL)
        self.set_fill_color(*HEADER_BG)
        self._th(lbl_w, HDR_H, 'Gaz')
        self.cell(num_w * 6, HDR_H, 'Numer zbiornika', border=1, align='C', fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self._th(lbl_w, HDR_H, '')
        for i in range(1, 7):
            self._th(num_w, HDR_H, str(i), align='C')
        self._advance(HDR_H)

        self._td(lbl_w, ROW_H, 'Ciśnienie [ bar ]')
        for i in range(1, 7):
            self._td(num_w, ROW_H, _v(getattr(obj, f'gaz_cisnienie_{i}')), align='C')
        self._advance(ROW_H)

        self._td(lbl_w, ROW_H, 'Wypełnienie [ % ]')
        for i in range(1, 7):
            self._td(num_w, ROW_H, _v(getattr(obj, f'gaz_wypelnienie_{i}')), align='C')
        self._advance(ROW_H + 0.8)

    def build_section_b(self, obj, b_rows):
        self._sec('B. Nadzór urządzeń kotłowych')

        lp_w  = 6
        war_w = 22
        uw_w  = 52
        kon_w = EFFECTIVE_W - lp_w - war_w - uw_w

        self._th(lp_w,  HDR_H, 'Lp.', align='C')
        self._th(kon_w, HDR_H, 'Kontrola')
        self._th(war_w, HDR_H, 'Wartość')
        self._th(uw_w,  HDR_H, 'UWAGI')
        self._advance(HDR_H)

        for row in b_rows:
            self._td(lp_w,  ROW_H, str(row['lp']), align='C', bold=True)
            self._td(kon_w, ROW_H, row['label'])
            self._td(war_w, ROW_H, _v(row['wartosc']))
            self._td(uw_w,  ROW_H, _v(row['uwagi']))
            self._advance(ROW_H)

        self.set_xy(MARGIN_LR, self.get_y() + 0.8)

    def build_signature(self, obj, field, name, margin_after=1.0):
        h_lbl = 3.5
        h_img = 6.0
        h_nam = 3.0
        total = h_lbl + h_img + h_nam
        x0, y0 = MARGIN_LR, self.get_y()

        self.rect(x0, y0, EFFECTIVE_W, total)

        self._f(bold=True, size=FS_SMALL)
        self.set_xy(x0 + 1, y0 + 0.5)
        self.cell(EFFECTIVE_W - 2, 3, 'Czytelny podpis:')

        sig_data = getattr(obj, field, '')
        if sig_data:
            try:
                raw = sig_data.split(',', 1)[1] if ',' in sig_data else sig_data
                img_bytes = base64.b64decode(raw)
                self.image(io.BytesIO(img_bytes), x=x0 + 1, y=y0 + h_lbl, h=h_img - 0.5)
            except Exception:
                pass

        self._f(bold=False, size=FS_SMALL)
        self.set_text_color(80, 80, 80)
        self.set_xy(x0 + 1, y0 + h_lbl + h_img + 0.3)
        self.cell(EFFECTIVE_W - 2, 2.5, name, border='T')
        self.set_text_color(0, 0, 0)

        self.set_xy(MARGIN_LR, y0 + total + margin_after)

    def build_laboratorium(self, obj):
        lab_name = ''
        if obj.laborant:
            lab_name = obj.laborant.get_full_name() or obj.laborant.username

        self._sec('LABOLATORIUM:')

        w1 = EFFECTIVE_W / 2
        w2 = EFFECTIVE_W - w1
        h  = ROW_H + 2.5
        x0, y0 = MARGIN_LR, self.get_y()

        for col_x, col_w, label, value in [
            (x0,      w1, 'Imię i Nazwisko',                lab_name),
            (x0 + w1, w2, 'Godzina przeprowadzenia analiz', obj.lab_godzina.strftime('%H:%M') if obj.lab_godzina else ''),
        ]:
            self.rect(col_x, y0, col_w, h)
            self._f(bold=True, size=FS_SMALL)
            self.set_xy(col_x + 1, y0 + 0.5)
            self.cell(col_w - 2, 3, label)
            self._f(bold=False, size=7)
            self.set_xy(col_x + 1, y0 + 3.5)
            self.cell(col_w - 2, 3, value)

        self.set_xy(MARGIN_LR, y0 + h + 0.5)

    def build_section_c(self, obj):
        self._sec('C. Analiza laboratoryjna wody')

        rodzaj_w = 20
        ozn_w    = 66
        jed_w    = 14
        gran_w   = 22
        wyn_w    = EFFECTIVE_W - rodzaj_w - ozn_w - jed_w - gran_w

        self._th(rodzaj_w, HDR_H, 'Rodzaj')
        self._th(ozn_w,    HDR_H, 'Oznaczenie')
        self._th(jed_w,    HDR_H, '')
        self._th(gran_w,   HDR_H, 'Granica tolerancji', align='C')
        self._th(wyn_w,    HDR_H, 'Wynik pomiaru')
        self._advance(HDR_H)

        wyglad = ('Wygląd – Ok: bezbarwna, klarowna i pozbawiona substancji'
                  ' rozpuszczonych / Nie: mętna')

        sections = [
            ('Woda zasilająca', [
                ('pH (w temp 25°C)',                 '',       '> 9',       _v(obj.wz_ph)),
                ('Wapniowce (twardość całkowita)',    '°dH',   '< 0,05',    _v(obj.wz_wapnioce_dh)),
                ('Tlen O2',                          'mg/litr','< 0,1',     _v(obj.wz_tlen_mg)),
                ('Przewodność elektryczna (org.)',    'µS/cm', '< 500',     _v(obj.wz_przewodnosc)),
                ('Temperatura',                      '°C',    '25 °C',     _v(obj.wz_temperatura)),
                (wyglad,                             '',      'Ok / Nie',  obj.wz_wyglad.upper() if obj.wz_wyglad else ''),
            ]),
            ('Kondensat', [
                ('pH (w temp 25°C)',                 '',       '',          _v(obj.k_ph)),
                ('Wapniowce (twardość całkowita)',    '°dH',   '< 0,05',    _v(obj.k_wapnioce_dh)),
                ('Przewodność elektryczna (org.)',    'µS/cm', '< 500',     _v(obj.k_przewodnosc)),
            ]),
            ('Woda kotłowa', [
                ('pH (w temp 25°C)',                 '',       '10,5 – 12', _v(obj.wk_ph)),
                ('Wapniowce (twardość całkowita)',    '°dH',   '< 0,05',    _v(obj.wk_wapnioce_dh)),
                ('Przewodność elektryczna (org.)',    'µS/cm', '30 – 8000', _v(obj.wk_przewodnosc)),
                (wyglad,                             '',      'Ok / Nie',  obj.wk_wyglad.upper() if obj.wk_wyglad else ''),
            ]),
            ('Woda po\nuzdatnianiu', [
                ('pH (w temp 25°C)',                 '',       '',          _v(obj.wu_ph)),
                ('Wapniowce (twardość całkowita)',    '°dH',   '< 0,1',     _v(obj.wu_wapnioce_dh)),
                ('Przewodność elektryczna (org.)',    'µS/cm', '',          _v(obj.wu_przewodnosc)),
            ]),
        ]

        for rodzaj, rows in sections:
            # Calculate height of each row based on Oznaczenie text length
            row_heights = []
            for ozn, _jed, _gran, _wyn in rows:
                lines = self._calc_lines(ozn, ozn_w)
                row_heights.append(lines * ROW_H)

            # Rodzaj cell height also needs wrapping check
            rodzaj_lines = self._calc_lines(rodzaj.replace('\n', ' '), rodzaj_w)
            block_h  = sum(row_heights)
            x0, y0   = MARGIN_LR, self.get_y()
            cx_jed   = x0 + rodzaj_w + ozn_w
            cx_gran  = cx_jed + jed_w
            cx_wyn   = cx_gran + gran_w

            # Merged Rodzaj cell
            self.rect(x0, y0, rodzaj_w, block_h)
            self._f(bold=True, size=FS)
            self.set_xy(x0 + 0.5, y0 + 0.5)
            self.multi_cell(rodzaj_w - 1, ROW_H, rodzaj, border=0, align='C')

            # Detail rows
            cum_y = y0
            for (ozn, jed, gran, wyn), rh in zip(rows, row_heights):
                # borders
                self.rect(x0 + rodzaj_w, cum_y, ozn_w,  rh)
                self.rect(cx_jed,        cum_y, jed_w,  rh)
                self.rect(cx_gran,       cum_y, gran_w, rh)
                self.rect(cx_wyn,        cum_y, wyn_w,  rh)

                # Oznaczenie — multi_cell for wrap
                self._f(size=FS)
                self.set_xy(x0 + rodzaj_w + 0.5, cum_y + 0.4)
                self.multi_cell(ozn_w - 1, ROW_H, ozn, border=0)

                # Single-value cells — vertically centered
                for cx, cw, txt, align in [
                    (cx_jed,  jed_w,  jed,  'C'),
                    (cx_gran, gran_w, gran, 'C'),
                    (cx_wyn,  wyn_w,  wyn,  'L'),
                ]:
                    self.set_xy(cx + 0.5, cum_y + (rh - FS * 0.352778) / 2)
                    self.cell(cw - 1, FS * 0.352778, txt, align=align)

                cum_y += rh

            self.set_xy(MARGIN_LR, y0 + block_h)

        self.set_xy(MARGIN_LR, self.get_y() + 0.8)

    def build_footer(self):
        self._f(bold=False, size=FS_SMALL)
        self.set_text_color(80, 80, 80)
        self.cell(EFFECTIVE_W * 0.8, 3.5,
                  'Gültig ab | Ważne od | Valable à partir du | Valid from: 23.07.2024',
                  border='T', new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(EFFECTIVE_W * 0.2, 3.5, '1 | 1', border='T', align='R')
        self.set_text_color(0, 0, 0)


def generate_formularz_pdf(obj, b_rows, now_str):
    pdf = KotlowniaPDF()
    pdf.build_header(obj, now_str)
    pdf.build_dzial_techniczny(obj)
    pdf.build_section_a(obj)
    pdf.build_section_b(obj, b_rows)

    tech_name = ''
    if obj.technician:
        tech_name = obj.technician.get_full_name() or obj.technician.username
    pdf.build_signature(obj, 'podpis_techniczny', tech_name, margin_after=1.5)

    pdf.build_laboratorium(obj)
    pdf.build_section_c(obj)

    lab_name = ''
    if obj.laborant:
        lab_name = obj.laborant.get_full_name() or obj.laborant.username
    pdf.build_signature(obj, 'podpis_laboratorium', lab_name, margin_after=1.0)

    pdf.build_footer()
    return bytes(pdf.output())
