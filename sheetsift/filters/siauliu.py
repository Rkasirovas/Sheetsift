import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_siauliu():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            required_columns = [
                'Sąskaitos Nr.',
                'Data',
                'Mokėjimo paskirtis',
                'Debetas',
                'Kreditas',
            ]

            if not all(col in df.columns for col in required_columns):
                return redirect(url_for('main.klaida'))

            df["METAI"] = pd.to_datetime(df["Data"], errors="coerce").dt.year
            df['ASMENS SĄSKAITA'] = df['Sąskaitos Nr.'].fillna('Sąskaita nenurodyta')
            df['MOKĖJIMO PASKIRTIS'] = df['Mokėjimo paskirtis'].fillna('Be paskirties')

            credit_df = df[df['Kreditas'] > 0].copy()

            credit_final = credit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'MOKĖJIMO PASKIRTIS'],
                columns='METAI', values='Kreditas', aggfunc='sum', fill_value=0).reset_index()

            debit_df = df[df['Debetas'] > 0].copy()

            debit_final = debit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'MOKĖJIMO PASKIRTIS'],
                columns='METAI', values='Debetas', aggfunc='sum', fill_value=0).reset_index()

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years if not pd.isna(y)]

            summary_list = []

            for account in df['Sąskaitos Nr.'].dropna().unique():
                account_credit = credit_df[credit_df['Sąskaitos Nr.'] == account]
                account_debit = debit_df[debit_df['Sąskaitos Nr.'] == account]

                credit_summary = account_credit.groupby('METAI')['Kreditas'].sum()
                debit_summary = account_debit.groupby('METAI')['Debetas'].sum()
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

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Israsai_Siauliu.xlsx')
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