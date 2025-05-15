import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_paysera():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            required_columns = [
                'Data ir laikas',
                'Gavėjas / Mokėtojas',
                'EVP / IBAN',
                'Suma ir valiuta',
                'Paskirtis',
                'Kreditas / Debetas',
            ]

            if not all(col in df.columns for col in required_columns):
                return redirect(url_for('main.klaida'))

            df["METAI"] = pd.to_datetime(df["Data ir laikas"], errors="coerce").dt.year
            df['Gavėjas/Mokėtojas'] = df['Gavėjas / Mokėtojas'].fillna('Nenurodytas')
            df['Gavėjo/Mokėtojo sąskaita'] = df['EVP / IBAN'].fillna('Sąskaita nenurodyta')
            df['MOKĖJIMO PASKIRTIS'] = df['Paskirtis'].fillna('Be paskirties')
            df['Suma'] = df['Suma ir valiuta'].fillna('Nenurodyta')

            credit_df = df[df['Kreditas / Debetas'] == 'K']

            credit_pivot = credit_df.pivot_table(
                index=['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita'],
                columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita']) \
                ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons,
                                    on=['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita'])

            credit_final = credit_final.rename(columns={
                'Gavėjas/Mokėtojas': 'MOKĖTOJAS',
                'Gavėjo/Mokėtojo sąskaita': 'MOKĖTOJO SĄSKAITA',
            })

            debit_df = df[df['Kreditas / Debetas'] == 'D']
            debit_df['Suma'] = debit_df['Suma'].abs()

            debit_pivot = debit_df.pivot_table(
                index=['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita'],
                columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita']) \
                ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons,
                                    on=['Gavėjas/Mokėtojas', 'Gavėjo/Mokėtojo sąskaita'])

            debit_final = debit_final.rename(columns={
                'Gavėjas/Mokėtojas': 'GAVĖJAS',
                'Gavėjo/Mokėtojo sąskaita': 'GAVĖJO SĄSKAITA'
            })

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years if not pd.isna(y)]

            credit_summary = credit_df.groupby('METAI')['Suma'].sum()
            debit_summary = debit_df.groupby('METAI')['Suma'].sum()

            credit_row = [credit_summary.get(year, 0) for year in all_years]
            debit_row = [debit_summary.get(year, 0) for year in all_years]

            credit_total = sum(credit_row)
            debit_total = sum(debit_row)

            credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                         index=['Bendros Pajamos'])

            debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                        index=['Bendros Išlaidos'])

            summary_combined = pd.concat([credit_df_row, debit_df_row])

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Išrasai_Paysera.xlsx')
            with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
                credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
                debit_final.to_excel(writer, sheet_name='Išlaidos', index=False)
                summary_combined.to_excel(writer, sheet_name='Bendra')

            session['last_file'] = result_path
            return redirect(url_for('main.sekmingai'))

        except Exception as e:
            print(f"Klaida: {e}")
            return redirect(url_for('main.klaida'))

    return redirect(url_for('main.klaida'))