import pandas as pd
import re
import os
from flask import request, redirect, url_for, current_app, session
from sheetsift.utils import schedule_file_deletion

def analyze_luminor():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            required_columns = [
                'Operacijos data',
                'Mokėjimo paskirtis',
                'Mokėtojas /\nGavėjas',
                'Mokėtojo / Gavėjo sąskaitos numeris, paslaugų teikėjo pavadinimas ir kodas',
                'Suma nac. valiuta (debetas)',
                'Suma nac. valiuta (kreditas)',
            ]

            if not all(col in df.columns for col in required_columns):
                return redirect(url_for('main.klaida'))

            df["METAI"] = pd.to_datetime(df["Operacijos data"], errors="coerce").dt.year
            df['Mokėtojas / Gavėjas'] = df['Mokėtojas /\nGavėjas'].fillna('Nenurodytas')
            df['Mokėjimo paskirtis'] = df['Mokėjimo paskirtis'].fillna('Be paskirties')

            def extract_account(text):
                match = re.search(r'(LT\d{18})', text)
                return match.group(0) if match else text

            df['Mokėtojo/Gavėjo sąskaita'] = df['Mokėtojo / Gavėjo sąskaitos numeris, paslaugų teikėjo pavadinimas ir kodas'].apply(extract_account)

            credit_df = df[df['Suma nac. valiuta (kreditas)'].notna()].copy()
            credit_pivot = credit_df.pivot_table(
                index=['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'],
                columns='METAI', values='Suma nac. valiuta (kreditas)', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])['Mokėjimo paskirtis'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons, on=['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])
            credit_final = credit_final.rename(columns={
                'Mokėtojas / Gavėjas': 'MOKĖTOJAS',
                'Mokėtojo/Gavėjo sąskaita': 'MOKĖTOJO SĄSKAITA',
                'Mokėjimo paskirtis': 'MOKĖJIMO PASKIRTIS'
            })

            debit_df = df[df['Suma nac. valiuta (debetas)'].notna()].copy()
            debit_pivot = debit_df.pivot_table(
                index=['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'],
                columns='METAI', values='Suma nac. valiuta (debetas)', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])['Mokėjimo paskirtis'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons, on=['Mokėtojas / Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])
            debit_final = debit_final.rename(columns={
                'Mokėtojas / Gavėjas': 'GAVĖJAS',
                'Mokėtojo/Gavėjo sąskaita': 'GAVĖJO SĄSKAITA',
                'Mokėjimo paskirtis': 'MOKĖJIMO PASKIRTIS'
            })

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years if not pd.isna(y)]

            credit_summary = credit_df.groupby('METAI')['Suma nac. valiuta (kreditas)'].sum()
            debit_summary = debit_df.groupby('METAI')['Suma nac. valiuta (debetas)'].sum()

            credit_row = [credit_summary.get(year, 0) for year in all_years]
            debit_row = [debit_summary.get(year, 0) for year in all_years]

            credit_total = sum(credit_row)
            debit_total = sum(debit_row)

            credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                         index=['Bendros Pajamos'])

            debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                        index=['Bendros Išlaidos'])

            summary_combined = pd.concat([credit_df_row, debit_df_row])

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Israsai_Luminor.xlsx')
            with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
                credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
                debit_final.to_excel(writer, sheet_name='Išlaidos', index=False)
                summary_combined.to_excel(writer, sheet_name='Bendra')

            schedule_file_deletion(result_path, delay=60)

            session['last_file'] = result_path
            return redirect(url_for('main.sekmingai'))

        except Exception as e:
            print(f"Klaida: {e}")
            return redirect(url_for('main.klaida'))

    return redirect(url_for('main.klaida'))