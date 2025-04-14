import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_seb():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            required_columns = [
                'DATA',
                'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS',
                'SĄSKAITA',
                'MOKĖJIMO PASKIRTIS',
                'SĄSKAITOS NR',
                'DEBETAS/KREDITAS'
            ]

            if not all(col in df.columns for col in required_columns):
                return redirect(url_for('main.klaida'))

            df["METAI"] = pd.to_datetime(df["DATA"], errors="coerce").dt.year
            df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'] = df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'].fillna('Nenurodytas')
            df['SĄSKAITA'] = df['SĄSKAITA'].fillna('Sąskaita nenurodyta')
            df['MOKĖJIMO PASKIRTIS'] = df['MOKĖJIMO PASKIRTIS'].fillna('Be paskirties')
            df['SĄSKAITOS NR'] = df['SĄSKAITOS NR'].fillna('Sąskaita nenurodyta')

            credit_df = df[df['DEBETAS/KREDITAS'] == 'C']

            credit_pivot = credit_df.pivot_table(
                index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])[
                'MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons,
                                    on=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])

            credit_final = credit_final.rename(columns={
                'SĄSKAITOS NR': 'ASMENS SĄSKAITA',
                'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': 'MOKĖTOJAS',
                'SĄSKAITA': 'MOKĖTOJO SĄSKAITA'
            })

            debit_df = df[df['DEBETAS/KREDITAS'] == 'D']

            debit_pivot = debit_df.pivot_table(
                index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])[
                'MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons,
                                   on=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])

            debit_final = debit_final.rename(columns={
                'SĄSKAITOS NR': 'ASMENS SĄSKAITA',
                'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': 'GAVĖJAS',
                'SĄSKAITA': 'GAVĖJO SĄSKAITA'
            })

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years if not pd.isna(y)]

            summary_list = []

            for account in df['SĄSKAITOS NR'].dropna().unique():
                account_credit = credit_df[credit_df['SĄSKAITOS NR'] == account]
                account_debit = debit_df[debit_df['SĄSKAITOS NR'] == account]

                credit_summary = account_credit.groupby('METAI')['SUMA'].sum()
                debit_summary = account_debit.groupby('METAI')['SUMA'].sum()
                credit_row = [credit_summary.get(year, 0) for year in all_years]
                debit_row = [debit_summary.get(year, 0) for year in all_years]
                credit_total = sum(credit_row)
                debit_total = sum(debit_row)
                credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                             index=[f'{account} Bendros Pajamos'])
                debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                            index=[f'{account} Bendros Išlaidos'])
                summary_list.append(credit_df_row)
                summary_list.append(debit_df_row)

            summary_combined = pd.concat(summary_list)

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Išrasai_SEB.xlsx')
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
