import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_swedbank():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            required_columns = [
                'Data',
                'Gavėjas / Siuntėjas',
                'Gavėjo / Siuntėjo sąskaitos nr.',
                'Sąskaitos Nr.',
                'Detalės',
                'Operacijos tipas',
            ]

            if not all(col in df.columns for col in required_columns):
                return redirect(url_for('main.klaida'))

            df["METAI"] = pd.to_datetime(df["Data"], errors="coerce").dt.year
            df['Gavėjas / Siuntėjas'] = df['Gavėjas / Siuntėjas'].fillna('Nenurodytas')
            df['Gavėjo / Siuntėjo sąskaitos nr.'] = df['Gavėjo / Siuntėjo sąskaitos nr.'].fillna('Sąskaita nenurodyta')
            df['Detalės'] = df['Detalės'].fillna('Be paskirties')
            df['Sąskaitos Nr.'] = df['Sąskaitos Nr.'].fillna('Sąskaita nenurodyta')

            credit_df = df[df['Operacijos tipas'] == 'įplaukos']

            credit_pivot = credit_df.pivot_table(
                index=['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.'],
                columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.']) \
                ['Detalės'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons,
                                    on=['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.'])

            credit_final = credit_final.rename(columns={
                'Sąskaitos Nr.': 'ASMENS SĄSKAITA',
                'Gavėjas / Siuntėjas': 'MOKĖTOJAS',
                'Gavėjo / Siuntėjo sąskaitos nr.': 'MOKĖTOJO SĄSKAITA',
                'Detalės': 'MOKĖJIMO PASKIRTIS'
            })

            debit_df = df[df['Operacijos tipas'] == 'išlaidos']
            debit_df['Suma'] = debit_df['Suma'].abs()

            debit_pivot = debit_df.pivot_table(
                index=['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.'],
                columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.']) \
                ['Detalės'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons,
                                    on=['Sąskaitos Nr.', 'Gavėjas / Siuntėjas', 'Gavėjo / Siuntėjo sąskaitos nr.'])

            debit_final = debit_final.rename(columns={
                'Sąskaitos Nr.': 'ASMENS SĄSKAITA',
                'Gavėjas / Siuntėjas': 'GAVĖJAS',
                'Gavėjo / Siuntėjo sąskaitos nr.': 'GAVĖJO SĄSKAITA',
                'Detalės': 'MOKĖJIMO PASKIRTIS'
            })

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years if not pd.isna(y)]

            summary_list = []

            for account in df['Sąskaitos Nr.'].dropna().unique():
                account_credit = credit_df[credit_df['Sąskaitos Nr.'] == account]
                account_debit = debit_df[debit_df['Sąskaitos Nr.'] == account]

                credit_summary = account_credit.groupby('METAI')['Suma'].sum()
                debit_summary = account_debit.groupby('METAI')['Suma'].sum()
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

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Išrasai_Swedbank.xlsx')
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