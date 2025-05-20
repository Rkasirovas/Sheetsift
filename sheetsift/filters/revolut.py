import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_revolut():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)
            columns = df.columns

            if 'Counterparty Name' in columns and 'Counterparty Account Nbr' in columns:
                df["METAI"] = pd.to_datetime(df["Started Date"], errors="coerce").dt.year
                df['Mokėtojas/Gavėjas'] = df['Counterparty Name'].fillna('Nenurodytas')
                df['Mokėtojo/Gavėjo sąskaitos numeris'] = df['Counterparty Account Nbr'].fillna('Sąskaita nenurodyta')
                df['MOKĖJIMO PASKIRTIS'] = df['Description'].fillna('Be paskirties')
                df['Amount'] = pd.to_numeric(df['Amount (base currency)'], errors='coerce').fillna(0)

                credit_df = df[df['Amount'] > 0].copy()
                debit_df = df[df['Amount'] < 0].copy()
                debit_df['Amount'] = debit_df['Amount'].abs()

                credit_pivot = credit_df.pivot_table(
                    index=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris'],
                    columns='METAI', values='Amount', aggfunc='sum', fill_value=0).reset_index()

                credit_reasons = credit_df.groupby(['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris']) \
                    ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

                credit_final = pd.merge(credit_pivot, credit_reasons,
                                        on=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris'])

                credit_final = credit_final.rename(columns={
                    'Mokėtojas/Gavėjas': 'MOKĖTOJAS',
                    'Mokėtojo/Gavėjo sąskaitos numeris': 'MOKĖTOJO SĄSKAITA'
                })

                debit_pivot = debit_df.pivot_table(
                    index=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris'],
                    columns='METAI', values='Amount', aggfunc='sum', fill_value=0).reset_index()

                debit_reasons = debit_df.groupby(['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris']) \
                    ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

                debit_final = pd.merge(debit_pivot, debit_reasons,
                                       on=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaitos numeris'])

                debit_final = debit_final.rename(columns={
                    'Mokėtojas/Gavėjas': 'GAVĖJAS',
                    'Mokėtojo/Gavėjo sąskaitos numeris': 'GAVĖJO SĄSKAITA'
                })

            elif all(col in columns for col in ['Started Date', 'Description', 'Amount', 'Type', 'Currency']):
                df["METAI"] = pd.to_datetime(df["Started Date"], errors="coerce").dt.year
                df['Description'] = df['Description'].fillna('Be paskirties')
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

                credit_df = df[df['Amount'] > 0].copy()
                debit_df = df[df['Amount'] < 0].copy()
                debit_df['Amount'] = debit_df['Amount'].abs()

                credit_final = credit_df.pivot_table(
                    index=['Description'],
                    columns='METAI', values='Amount', aggfunc='sum', fill_value=0).reset_index()

                credit_final = credit_final.rename(columns={'Description': 'MOKĖTOJAS'})

                debit_final = debit_df.pivot_table(
                    index=['Description'],
                    columns='METAI', values='Amount', aggfunc='sum', fill_value=0).reset_index()

                debit_final = debit_final.rename(columns={'Description': 'GAVĖJAS'})

            else:
                return redirect(url_for('main.klaida'))

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years]

            credit_summary = credit_df.groupby('METAI')['Amount'].sum()
            debit_summary = debit_df.groupby('METAI')['Amount'].sum()

            credit_row = [credit_summary.get(year, 0) for year in all_years]
            debit_row = [debit_summary.get(year, 0) for year in all_years]

            credit_total = sum(credit_row)
            debit_total = sum(debit_row)

            credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                         index=['Bendros Pajamos'])
            debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                        index=['Bendros Išlaidos'])

            summary_combined = pd.concat([credit_df_row, debit_df_row])

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Israsai_Revolut.xlsx')
            with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
                credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
                debit_final.to_excel(writer, sheet_name='Išlaidos', index=False)
                summary_combined.reset_index().rename(columns={'index': ''}).to_excel(writer, sheet_name='Bendra', index=False)

            session['last_file'] = result_path
            return redirect(url_for('main.sekmingai'))

        except Exception as e:
            print(f"Klaida: {e}")
            return redirect(url_for('main.klaida'))

    return redirect(url_for('main.klaida'))