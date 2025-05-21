import pandas as pd
import os
import re
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

            def extract_info(text):
                moketojas = re.search(r'MOKĖTOJAS:\s*(.+)', text)
                gavejas = re.search(r'GAVĖJAS:\s*(.+)', text)
                saskaita = re.search(r'LT\d{18}', text)

                paskirtis_match = re.search(r'(?i)(Mok(?:ėjimo)?\.? ?paskirtis)[:：]?\s*(.+)', text)
                paskirtis = paskirtis_match.group(2).strip() if paskirtis_match else 'Be paskirties'

                return pd.Series({
                    'MOKĖTOJAS': moketojas.group(1).strip() if moketojas else 'Nenurodytas',
                    'GAVĖJAS': gavejas.group(1).strip() if gavejas else 'Nenurodytas',
                    'SĄSKAITOS NUMERIS': saskaita.group(0) if saskaita else 'Sąskaita nenurodyta',
                    'MOKĖJIMO PASKIRTIS': paskirtis,
                })

            info_df = df['Mokėjimo paskirtis'].fillna('').apply(extract_info)
            df = pd.concat([df, info_df], axis=1)

            credit_df = df[df['Kreditas'] > 0].copy()
            credit_df['PAJAMOS'] = credit_df['Kreditas']
            credit_pivot = credit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'MOKĖTOJAS', 'SĄSKAITOS NUMERIS'],
                columns='METAI', values='PAJAMOS', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['ASMENS SĄSKAITA', 'MOKĖTOJAS', 'SĄSKAITOS NUMERIS'])['MOKĖJIMO PASKIRTIS'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons, on=['ASMENS SĄSKAITA', 'MOKĖTOJAS', 'SĄSKAITOS NUMERIS'])
            credit_final = credit_final.rename(columns={'SĄSKAITOS NUMERIS': 'MOKĖTOJO SĄSKAITA'})

            debit_df = df[df['Debetas'] > 0].copy()
            debit_df['IŠLAIDOS'] = debit_df['Debetas']
            debit_pivot = debit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'GAVĖJAS', 'SĄSKAITOS NUMERIS'],
                columns='METAI', values='IŠLAIDOS', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['ASMENS SĄSKAITA', 'GAVĖJAS', 'SĄSKAITOS NUMERIS'])['MOKĖJIMO PASKIRTIS'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons, on=['ASMENS SĄSKAITA', 'GAVĖJAS', 'SĄSKAITOS NUMERIS'])
            debit_final = debit_final.rename(columns={'SĄSKAITOS NUMERIS': 'GAVĖJO SĄSKAITA'})

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years]

            summary_list = []

            for account in df['ASMENS SĄSKAITA'].dropna().unique():
                account_credit = credit_df[credit_df['ASMENS SĄSKAITA'] == account]
                account_debit = debit_df[debit_df['ASMENS SĄSKAITA'] == account]

                credit_summary = account_credit.groupby('METAI')['PAJAMOS'].sum()
                debit_summary = account_debit.groupby('METAI')['IŠLAIDOS'].sum()

                credit_row = [credit_summary.get(year, 0) for year in all_years]
                debit_row = [debit_summary.get(year, 0) for year in all_years]

                credit_total = sum(credit_row)
                debit_total = sum(debit_row)

                credit_df_row = pd.DataFrame(
                    [credit_row + [credit_total]], columns=all_years + ['Viso'],
                    index=[f'{account} Bendros Pajamos']
                )
                debit_df_row = pd.DataFrame(
                    [debit_row + [debit_total]], columns=all_years + ['Viso'],
                    index=[f'{account} Bendros Išlaidos']
                )

                summary_list.append(credit_df_row)
                summary_list.append(debit_df_row)

            summary_combined = pd.concat(summary_list)

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Israsai_Siauliu.xlsx')
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